from decimal import Decimal
from eth_account import Account
from fastapi import HTTPException, status
from web3 import Web3
from utils.web3_client import Web3Client
from storage.wallet_repository import WalletRepository
from API_Layer.Interfaces.wallet_interface import BalanceResponse, SearchResponse, TransferRequest
from dotenv import load_dotenv
from .authentication_service import AuthenticationService
from DataAccess_Layer.dao.wallet_dao import WalletDAO

import os
from DataAccess_Layer.utils.session import get_db

load_dotenv()
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"},
                   {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
]


class WalletService:
    def __init__(self, db=None):
        self.web3 = Web3Client().w3
        self.repo = WalletRepository()

        self.usdc_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(
                "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
            ),
            abi=ERC20_ABI
        )
        self.usdt_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7"),
            abi=ERC20_ABI)
        self.db = db
        self.dao = WalletDAO(self.db)
        # self.user_dao = UserAuthDAO(self.db)

    def check_contract(self):
        code = self.web3.eth.get_code(
            self.web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        )
        # name = self.usdt_contract.functions.name().call()
        # symbol = self.usdt_contract.functions.symbol().call()
        # decimals = self.usdt_contract.functions.decimals().call()

        # print(name, symbol, decimals)
        raw_balance = self.usdt_contract.functions.balanceOf(self.web3.to_checksum_address("0x0B31AA8d667B056c8911CAE4b62f2b5Af8C8271a")).call()
        print(raw_balance)


        # print(code)

    def create_wallet(self):
        account = Account.create()
        self.repo.save(account.address, account.key.hex())
        return account

    def check_balance(self, address: str):
        if not self.web3.is_address(address):
            raise HTTPException(400, "Invalid address")

        address = self.web3.to_checksum_address(address)
        balance_wei = self.web3.eth.get_balance(address)
        balance_eth = self.web3.from_wei(balance_wei, "ether")

        try:
            raw = self.usdc_contract.functions.balanceOf(address).call()
            decimals = self.usdc_contract.functions.decimals().call()
            usdc = raw / (10 ** decimals)
        except:
            usdc = 0.0

        return BalanceResponse(
            address=address,
            # balance_wei=balance_wei,
            # balance_eth=float(balance_eth),
            balance_usdc=float(usdc)
        )
    
    def list_wallets(self):
        """
        List all wallets stored in wallets.json
        (private keys are NEVER exposed)
        """
        try:
            users = self.dao.get_all_users()
            wallets = [{"user_id": u.customer_id, "email": u.mail, "address": u.wallet_address} for u in users]
            safe_wallets = []

            for w in wallets:
                address = self.web3.to_checksum_address(w["address"])

                # ETH balance
                eth_balance_wei = self.web3.eth.get_balance(address)
                eth_balance = float(
                    self.web3.from_wei(eth_balance_wei, "ether")
                )

                # USDC balance
                try:
                    usdc_raw = self.usdc_contract.functions.balanceOf(address).call()
                    usdc_decimals = self.usdc_contract.functions.decimals().call()
                    usdc_balance = usdc_raw / (10 ** usdc_decimals)
                except Exception:
                    usdc_balance = 0.0

                safe_wallets.append({
                    "user_id": w["user_id"],
                    "email": w["email"],
                    "address": w["address"],
                    "balance_eth": eth_balance,
                    "balance_usdc": float(usdc_balance)
                })

            return {
                "total_wallets": len(safe_wallets),
                "wallets": safe_wallets
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def create_free_tokens(self, request):
        from_address = os.getenv("MAIN_WALLET_ADDRESS")
        private_key = self.dao.get_private_key_by_address(from_address)
        if not self.web3.is_address(request.address):
            raise HTTPException(400, "Invalid address")
        to_address = self.web3.to_checksum_address(request.address)
        checksum_main_address = self.web3.to_checksum_address(from_address)
        # if request.type.upper() == "USDC" and self.usdc_contract.functions.balanceOf(checksum_main_address).call()<request.amount*10**6:
        #     raise HTTPException(400, "Faucet is out of USDC funds")
        # if request.type.upper() == "ETH" and self.web3.eth.get_balance(checksum_main_address)<self.web3.to_wei(request.amount, "ether"):
        #     raise HTTPException(400, "Faucet is out of ETH funds")
        # if request.type.upper() == "USDT" and self.usdt_contract.functions.balanceOf(checksum_main_address).call()<request.amount*10**6:
        #     raise HTTPException(400, "Faucet is out of USDT funds")

        nonce = self.web3.eth.get_transaction_count(from_address)

        cust_fiat_bank_balance = self.dao.get_fiat_bank_balance_by_wallet_address(request.address)
        print(f"Customer's fiat bank balance: {cust_fiat_bank_balance}")

        if request.type.upper() == "USDC":
            INR_RATE = Decimal("21.83")   # stablecoin INR example
        elif request.type.upper() == "ETH":
            INR_RATE = Decimal("100")   # ETH INR example\
        elif request.type.upper() == "USDT":
            INR_RATE = Decimal("21.83")   # stablecoin INR example
        token_amount = Decimal(str(request.amount))
        token_inr_value = token_amount * INR_RATE
        print(f"Token INR value: {token_inr_value}")
        print(f"Type of token_inr_value: {type(token_inr_value)}")

        if cust_fiat_bank_balance < token_inr_value:
            raise HTTPException(400, "Insufficient fiat balance in bank account to cover the requested tokens")
        
        

        if request.type.upper() == "ETH":
            tx = {
                "nonce": nonce,
                "to": to_address,
                "value": self.web3.to_wei(request.amount, "ether"),
                "gas": 21000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            }

        elif request.type.upper() == "USDC":
            decimals = self.usdc_contract.functions.decimals().call()
            amount = int(request.amount * (10 ** decimals))
            tx = self.usdc_contract.functions.transfer(
                to_address, amount
            ).build_transaction({
                "from": from_address,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            })
        elif request.type.upper() == "USDT":
            decimals = self.usdt_contract.functions.decimals().call()
            amount = int(request.amount * (10 ** decimals))
            tx = self.usdt_contract.functions.transfer(
                to_address, amount
            ).build_transaction({
                "from": from_address,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            })
        else:
            raise HTTPException(400, "Unsupported asset")

        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

        raw_tx = (
            signed_tx.raw_transaction
            if hasattr(signed_tx, "raw_transaction")
            else signed_tx.rawTransaction
        )

        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
        print(f"Transaction hash: {tx_hash.hex()}")
        # Update customer's fiat bank balance
        try:
            # Deduct from customer
            new_balance = cust_fiat_bank_balance - token_inr_value
            print(f"New fiat bank balance for customer: {new_balance}")
            self.dao.update_fiat_bank_balance_by_wallet_address(
                request.address,
                new_balance
            )

            # Credit admin
            result =self.dao.update_admin_fiat_bank_balance(token_inr_value)
            print(f"Credited {token_inr_value} to admin's fiat bank balance", result)

        except Exception:
            self.db.rollback()
            raise HTTPException(500, "Failed to update fiat balances")


        return {"tx_hash": tx_hash.hex(), "status": "submitted", "your new fiat_bank_balance": float(new_balance), "message": f"Successfully transferred {request.amount} {request.type}"}




    def transfer(self, req: TransferRequest):
        # check if from address is valid
        if not self.web3.is_address(req.from_address):
            raise HTTPException(400, "Invalid Your address")
        # check if to address is valid
        if not self.web3.is_address(req.to_address):
            raise HTTPException(400, "Invalid Receiveraddress")
        # Check if the sender and receiver addresses are the same
        if req.from_address.lower() == req.to_address.lower():
            raise HTTPException(400, "Sender and receiver addresses cannot be the same")
        from_addr = self.web3.to_checksum_address(req.from_address)
        to_addr = self.web3.to_checksum_address(req.to_address)

        private_key = self.dao.get_private_key_by_address(req.from_address)
        if not private_key:
            raise HTTPException(404, "User not found")


        # account = Account.from_key(req.private_key)
        # if account.address != from_addr:
        #     raise HTTPException(400, "Private key mismatch")

        nonce = self.web3.eth.get_transaction_count(from_addr)

        if req.asset.upper() == "ETH":
            tx = {
                "nonce": nonce,
                "to": to_addr,
                "value": self.web3.to_wei(req.amount, "ether"),
                "gas": 21000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            }

        elif req.asset.upper() == "USDC":
            decimals = self.usdc_contract.functions.decimals().call()
            amount = int(req.amount * (10 ** decimals))
            tx = self.usdc_contract.functions.transfer(
                to_addr, amount
            ).build_transaction({
                "from": from_addr,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            })
        else:
            raise HTTPException(400, "Unsupported asset")

        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

        raw_tx = (
            signed_tx.raw_transaction
            if hasattr(signed_tx, "raw_transaction")
            else signed_tx.rawTransaction
        )

        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
        print(f"Transaction hash: {tx_hash.hex()}")
        if to_addr.lower() == os.getenv("MAIN_WALLET_ADDRESS").lower() and tx_hash!="":
            # If the transfer is to the main wallet and asset is USDC, credit the admin's fiat balance
            INR_RATE = Decimal("21.83")   # stablecoin INR example
            token_amount = Decimal(str(req.amount))
            token_inr_value = token_amount * INR_RATE
            try:
                # deduct from admin
                result =self.dao.update_admin_fiat_bank_balance(-token_inr_value)
                print(f"Deducted {token_inr_value} from admin's fiat bank balance", result)
                # Credit to customer
                cust_fiat_bank_balance = self.dao.get_fiat_bank_balance_by_wallet_address(from_addr)

                new_balance = cust_fiat_bank_balance + token_inr_value

                self.dao.update_fiat_bank_balance_by_wallet_address(from_addr, new_balance)
                print(f"Credited {token_inr_value} to customer's fiat bank balance", new_balance)
            except Exception:
                self.db.rollback()
                raise HTTPException(500, "Failed to update fiat balances")
        return {"tx_hash": tx_hash.hex(), "status": "submitted", "fiat_bank_balance": float(new_balance)}
    
    def verify_address(self, address):
        try:
            if not self.web3.is_address(address):
                return False
            return True
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(500, str(e))

    
    def get_balance(self, address: str):
        fiat_balance = self.dao.get_fiat_bank_balance_by_wallet_address(address)
        if not self.web3.is_address(address):
            raise HTTPException(status_code=400, detail="Invalid address")

        address = self.web3.to_checksum_address(address)



        # tokens = [
        #     {"symbol": "USDC", "contract": self.usdc_contract, "decimals": 6},
        # ]

        # stablecoins = []
        # total_value = 0

        # for token in tokens:
        #     raw_balance = token["contract"].functions.balanceOf(address).call()
        #     balance = raw_balance / (10 ** token["decimals"])

        #     if balance > 0:
        #         stablecoins.append({
        #             "symbol": token["symbol"],
        #             "balance": balance
        #         })
        #         total_value += balance

        # total_fiat = fiat_balance

        # return {
        #     "totalFiat": round(total_fiat, 2),
        #     "stablecoins": stablecoins,
        #     "totalStablecoinValue": round(total_value, 2)
        # }
    
    def search_users(self, query: str):

        # First search in bank_customer_details
        users = self.dao.get_users_by_search_query(query)

        # If found → return immediately
        if users:
            return [
                {
                    "customer_id": user.customer_id,
                    "name": user.name,
                    "phone_number": user.phone_number,
                    "wallet_address": user.wallet_address
                }
                for user in users
            ]
    def search_payees(self, customer_id: str, query: str):

        payees = self.dao.search_payees_for_customer(customer_id, query)

        return [
            {
                "customer_id": str(customer_id),
                "name": payee.payee_name,
                "phone_number": payee.phone_number,
                "wallet_address": payee.wallet_address
            }
            for payee in payees
        ]

        
        
        
    def get_fiat_balance_by_customer_id(self, customer_id: str):
        result = self.dao.get_fiat_balance_by_customer_id(customer_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        bank_account_number, fiat_bank_balance = result
        return {
            "bank_account_number": bank_account_number,
            "fiat_bank_balance": float(fiat_bank_balance)
            if fiat_bank_balance is not None else 0.0
        }
            
    def burn_tokens(self, request):
        from_address = os.getenv("MAIN_WALLET_ADDRESS")
        private_key = self.dao.get_private_key_by_address(from_address)
        if not self.web3.is_address(request.address):
            raise HTTPException(400, "Invalid address")
        to_address = self.web3.to_checksum_address(request.address)
    
        nonce = self.web3.eth.get_transaction_count(from_address)

        cust_fiat_bank_balance = self.dao.get_fiat_bank_balance_by_wallet_address(request.address)
        print(f"Customer's fiat bank balance: {cust_fiat_bank_balance}")

        INR_RATE = Decimal("21.83")   # stablecoin INR example
        token_amount = Decimal(str(request.amount))
        token_inr_value = token_amount * INR_RATE
        print(f"Token INR value: {token_inr_value}")
        print(f"Type of token_inr_value: {type(token_inr_value)}")

        
        if request.type.upper() == "ETH":
            tx = {
                "nonce": nonce,
                "to": to_address,
                "value": self.web3.to_wei(request.amount, "ether"),
                "gas": 21000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            }

        elif request.type.upper() == "USDC":
            decimals = self.usdc_contract.functions.decimals().call()
            amount = int(request.amount * (10 ** decimals))
            tx = self.usdc_contract.functions.transfer(
                to_address, amount
            ).build_transaction({
                "from": from_address,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": self.web3.eth.chain_id
            })
        else:
            raise HTTPException(400, "Unsupported asset")

        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

        raw_tx = (
            signed_tx.raw_transaction
            if hasattr(signed_tx, "raw_transaction")
            else signed_tx.rawTransaction
        )

        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
        print(f"Transaction hash: {tx_hash.hex()}")
        # Update customer's fiat bank balance
        try:
            # Add to customer
            new_balance = cust_fiat_bank_balance + token_inr_value
            print(f"New fiat bank balance for customer: {new_balance}")
            self.dao.update_fiat_bank_balance_by_wallet_address(
                request.address,
                new_balance
            )

            # deduct from admin
            result =self.dao.update_admin_fiat_bank_balance(-token_inr_value)
            print(f"Deducted {token_inr_value} from admin's fiat bank balance", result)

        except Exception:
            self.db.rollback()
            raise HTTPException(500, "Failed to update fiat balances")