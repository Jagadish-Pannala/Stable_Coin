from decimal import Decimal
from eth_account import Account
from fastapi import HTTPException, status
from DataAccess_Layer.utils.price import get_usd_to_inr_rate
from utils.web3_client import Web3Client
from storage.wallet_repository import WalletRepository
from API_Layer.Interfaces.wallet_interface import BalanceResponse, SearchResponse, TransferRequest, BalResponse
from dotenv import load_dotenv
from DataAccess_Layer.dao.wallet_dao import WalletDAO
from DataAccess_Layer.dao.tenant_dao import TenantDAO
from DataAccess_Layer.dao.token_dao import TokenDAO
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
from Business_Layer.transaction_history_service import TransactionService
import os
from DataAccess_Layer.utils.session import get_db
import logging
from utils.redis_client import RedisClient


logger = logging.getLogger(__name__)

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
        self.tenant_dao = TenantDAO(self.db)
        self.token_dao = TokenDAO(self.db)
        self.user_dao = UserAuthDAO(self.db)
        self.redis = RedisClient()


    def _invalidate_transaction_cache(self):
        """Invalidate transaction history cache after blockchain transactions"""
        try:
            tx_service = TransactionService()
            tx_service.invalidate_transaction_cache()
        except Exception as e:
            logger.warning(f"Cache invalidation failed (non-critical): {e}")
    
    def check_contract(self, address):
        # code = self.web3.eth.get_code(
        #     self.web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        # )
        # name = self.usdt_contract.functions.name().call()
        # symbol = self.usdt_contract.functions.symbol().call()
        # decimals = self.usdt_contract.functions.decimals().call()

        # print(name, symbol, decimals)
        # raw_balance = self.usdt_contract.functions.balanceOf(self.web3.to_checksum_address("0x0B31AA8d667B056c8911CAE4b62f2b5Af8C8271a")).call()
        # print(raw_balance)
        # available_functions = self.usdt_contract.all_functions()
        # return [func.fn_name for func in available_functions]
        eth_balance = self.web3.eth.get_balance(address)
        balance_eth = self.web3.from_wei(eth_balance, "ether")
        return balance_eth



    def create_wallet(self):
        account = Account.create()
        self.repo.save(account.address, account.key.hex())
        return account

    def check_balance(self, address: str) -> BalResponse:
        try:
            if not self.web3.is_address(address):
                raise HTTPException(status_code=400, detail="Invalid address")

            address = self.web3.to_checksum_address(address)

            # ================= CACHE READ =================
            cached_balance = self.redis.get_wallet_balance(address.lower())
            
            if cached_balance:
                logger.info(f"✅ Wallet balance served from cache for {address.lower()}")
                return BalResponse(**cached_balance)



            fiat_total_balance = self.dao.get_fiat_bank_balance_by_wallet_address(address)

            # Native ETH balance (optional)
            balance_wei = self.web3.eth.get_balance(address)
            balance_eth = self.web3.from_wei(balance_wei, "ether")

            tenant_id = self.dao.get_tenant_id_by_address(address)

            stablecoin_balance = []
            total_stablecoin_value = 0

            # ======================================================
            # CASE 1 — TENANT HAS NO CUSTOM TOKENS (DEFAULT TOKENS)
            # ======================================================
            if not self.tenant_dao.tenant_has_tokens(tenant_id):

                default_tokens = [
                    {"symbol": "USDC", "contract": self.usdc_contract},
                    {"symbol": "USDT", "contract": self.usdt_contract},
                    # {"symbol": "DAI", "contract": self.dai_contract},
                ]

                for token in default_tokens:
                    try:
                        decimals = token["contract"].functions.decimals().call()
                        raw_balance = token["contract"].functions.balanceOf(address).call()

                        balance = raw_balance / (10 ** decimals)

                        stablecoin_balance.append({
                            "symbol": token["symbol"],
                            "balance": balance
                        })

                        total_stablecoin_value += balance

                    except Exception:
                        continue

            # ======================================================
            # CASE 2 — TENANT HAS CUSTOM TOKENS
            # ======================================================
            else:

                from Business_Layer.onchain_sepolia_gateway.services.onchain_token_service import (
                    OnchainTokenService,
                )

                tenant = self.tenant_dao.get_tenant_by_id(tenant_id)

                tokens = self.token_dao.get_tokens_by_tenant(tenant_id)

                for token in tokens:
                    print(f"Checking balance for {token.token_symbol} at {token.contract_address}")

                    token_service = OnchainTokenService()

                    token_service.configure(
                        tenant.rpc_url,
                        token.contract_address,
                        token.encrypted_private_key,
                        tenant.chain_id
                    )

                    decimals = token.decimals or 18

                    balance = token_service.get_balance_with_decimals(
                        address
                    )

                    stablecoin_balance.append({
                        "symbol": token.token_symbol,
                        "balance": balance
                    })

                    total_stablecoin_value += balance

            response = BalResponse(
                totalFiat=fiat_total_balance,
                stablecoins=stablecoin_balance,
                totalStablecoinValue=total_stablecoin_value
            ).dict()

            # ================= CACHE WRITE =================
            self.redis.set_wallet_balance(address.lower(), response, ttl=60)

            return BalResponse(**response)

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        
    
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
        try:
            if not self.web3.is_address(request.address):
                raise HTTPException(400, "Invalid address")

            to_address = self.web3.to_checksum_address(request.address)

            tenant_id = self.dao.get_tenant_id_by_address(to_address)

            token_amount = Decimal(str(request.amount))
            token_type = request.type.upper()

            # -----------------------------
            # Fiat Conversion
            # -----------------------------
            if request.type.upper() in ["USDC", "USDT"]:
                INR_RATE = get_usd_to_inr_rate()
            elif request.type.upper() == "ETH":
                INR_RATE = Decimal("100")
            else:
                raise HTTPException(400, "Unsupported asset")

            token_inr_value = token_amount * INR_RATE

            cust_balance = self.dao.get_fiat_bank_balance_by_wallet_address(
                to_address
            )

            if cust_balance < token_inr_value:
                raise HTTPException(400, "Insufficient fiat balance")

            # ======================================================
            # CASE 1 — TENANT HAS NO TOKENS (DEFAULT NETWORK TRANSFER)
            # ======================================================
            if not self.tenant_dao.tenant_has_tokens(tenant_id):

                from_address = self.web3.to_checksum_address(
                    os.getenv("MAIN_WALLET_ADDRESS")
                )

                private_key = self.dao.get_private_key_by_address(from_address)

                nonce = self.web3.eth.get_transaction_count(
                    from_address,
                    "pending"
                )

                if token_type == "ETH":

                    tx = {
                        "from": from_address,
                        "to": to_address,
                        "value": self.web3.to_wei(token_amount, "ether"),
                        "nonce": nonce,
                        "chainId": self.web3.eth.chain_id,
                        "gasPrice": self.web3.eth.gas_price,
                        "gas": 21000
                    }

                else:
                    contract = (
                        self.usdc_contract
                        if token_type == "USDC"
                        else self.usdt_contract
                    )

                    decimals = contract.functions.decimals().call()
                    amount = int(token_amount * (10 ** decimals))

                    tx = contract.functions.transfer(
                        to_address,
                        amount
                    ).build_transaction({
                        "from": from_address,
                        "nonce": nonce,
                        "chainId": self.web3.eth.chain_id,
                        "gasPrice": self.web3.eth.gas_price,
                    })

                    tx["gas"] = self.web3.eth.estimate_gas(tx)

                signed_tx = self.web3.eth.account.sign_transaction(
                    tx,
                    private_key
                )

                raw_tx = (
                    signed_tx.raw_transaction
                    if hasattr(signed_tx, "raw_transaction")
                    else signed_tx.rawTransaction
                )

                tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt.status != 1:
                    raise HTTPException(400, "Transaction failed")

            # ======================================================
            # CASE 2 — TENANT HAS OWN TOKEN CONFIG
            # ======================================================
            else:
                print("Tenant tokens detected → Onchain mint")

                from Business_Layer.onchain_sepolia_gateway.services.onchain_token_service import (
                    OnchainTokenService,
                )

                tenant = self.tenant_dao.get_tenant_by_id(tenant_id)
                admin = self.user_dao.get_admin_details(tenant_id)
                admin_address = admin.wallet_address
                admin_balance = token_service.get_balance_with_decimals(admin_address)
                if admin_balance < token_amount:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Transfer cannot be processed: Admin wallet has only "
                            f"{admin_balance} {token_type}, but {token_amount} requested."
                        )
                    )
                private_key = admin.encrypted_private_key
                rpc_url = tenant.rpc_url
                chain_id = tenant.chain_id

                # Fetch token dynamically
                token_config = self.token_dao.get_token_by_symbol(
                    tenant_id,
                    token_type
                )

                if not token_config:
                    raise HTTPException(
                        400,
                        f"{token_type} not configured for tenant"
                    )

                if not token_config.mint_enabled:
                    raise HTTPException(
                        400,
                        f"Mint disabled for {token_type}"
                    )

                contract_address = token_config.contract_address
                # private_key = token_config.encrypted_private_key
                decimals = token_config.decimals or 18

                token_service = OnchainTokenService()
                token_service.configure(
                    rpc_url,
                    contract_address,
                    private_key,
                    chain_id
                )

                tx_hash = token_service.transfer(
                    to_address,
                    token_amount
                )

            # ======================================================
            # Fiat Settlement
            # ======================================================
            new_balance = cust_balance - token_inr_value

            self.dao.update_fiat_bank_balance_by_wallet_address(
                to_address,
                new_balance
            )

            self.dao.update_admin_fiat_bank_balance(tenant_id,
                token_inr_value
            )

            # invalidate cache
            self._invalidate_transaction_cache()

            # Invalidate wallet balance cache
            self.redis.invalidate_wallet_balance(to_address.lower())

            logger.info(
                f"🗑️ Wallet balance cache invalidated for {to_address.lower()}"
            )


            return {
                "tx_hash": tx_hash if isinstance(tx_hash, str) else tx_hash.hex(),
                "status": "confirmed",
                "new_fiat_bank_balance": float(new_balance)
            }

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(500, detail=str(e))




    def transfer(self, req: TransferRequest):
        try:
            if not self.web3.is_address(req.from_address):
                raise HTTPException(400, "Invalid address")

            address = self.web3.to_checksum_address(req.from_address)

            tenant_id = self.dao.get_tenant_id_by_address(address)
            
            asset = req.asset.upper()
            
            # 1 Validate addresses

            if not self.web3.is_address(req.from_address):
                raise HTTPException(400, "Invalid sender address")

            if not self.web3.is_address(req.to_address):
                raise HTTPException(400, "Invalid receiver address")

            if req.from_address.lower() == req.to_address.lower():
                raise HTTPException(400, "Sender and receiver cannot be same")
            
            # checking if the from address is the main wallet
            if req.from_address.lower() == os.getenv("MAIN_WALLET_ADDRESS").lower():
                raise HTTPException(400, "Sender cannot be the main wallet, If you to get tokens using another api '/free-tokens'")
            
            if req.to_address.lower() == os.getenv("MAIN_WALLET_ADDRESS").lower():
                admin_balance = self.dao.get_fiat_bank_balance_by_wallet_address(
                    os.getenv("MAIN_WALLET_ADDRESS")
                )
                INR_RATE = get_usd_to_inr_rate()
                print("inr rate", INR_RATE)
                token_inr_value = Decimal(str(req.amount)) * INR_RATE
                print("token inr value", token_inr_value)
                if admin_balance < token_inr_value:
                    raise HTTPException(400, "Admin has insufficient fiat balance to burn tokens")
            
            
            if not self.tenant_dao.tenant_has_tokens(tenant_id):

                from_addr = self.web3.to_checksum_address(req.from_address)
                to_addr = self.web3.to_checksum_address(req.to_address)
                main_wallet = self.web3.to_checksum_address(
                    os.getenv("MAIN_WALLET_ADDRESS")
                )

                # 2 Load contract
                
                contract = self._get_contract(asset)

                # 3 Get private key
                
                private_key = self.dao.get_private_key_by_address(from_addr)
                if not private_key:
                    raise HTTPException(404, "User not found")
                
                # 4 Convert amount safely
                
                decimals = contract.functions.decimals().call()
                token_amount = Decimal(str(req.amount))
                amount = int(token_amount * (10 ** decimals))

                # 5 Check token balance
                
                balance = contract.functions.balanceOf(from_addr).call()
                if balance < amount:
                    raise HTTPException(400, "Insufficient token balance")


                # 6 Nonce (pending safe)
                
                nonce = self.web3.eth.get_transaction_count(
                    from_addr, "pending"
                )

                # 7 Build tx
                
                tx = contract.functions.transfer(
                    to_addr,
                    amount
                ).build_transaction({
                    "from": from_addr,
                    "nonce": nonce,
                    "chainId": self.web3.eth.chain_id,
                    "gasPrice": self.web3.eth.gas_price
                })

                tx["gas"] = self.web3.eth.estimate_gas(tx)
                print(f"Estimated gas: {tx['gas']}")
                
                # 8 Sign + Send
                
                signed_tx = self.web3.eth.account.sign_transaction(
                    tx, private_key
                )

                raw_tx = (
                    signed_tx.raw_transaction
                    if hasattr(signed_tx, "raw_transaction")
                    else signed_tx.rawTransaction
                )

                tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
                
                # 9 WAIT FOR CONFIRMATION
                
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt.status != 1:
                    raise HTTPException(400, "Transaction failed on-chain")

                # 10 Fiat Settlement (Burn Logic)
                
                transfer_type = "Transfer"

                if to_addr.lower() == main_wallet.lower() and tx_hash!="":

                    transfer_type = "Burn"

                    self.dao.update_admin_fiat_bank_balance(tenant_id,
                        -token_inr_value
                    )

                    cust_balance = (
                        self.dao.get_fiat_bank_balance_by_wallet_address(
                            from_addr
                        )
                    )

                    new_balance = float(cust_balance) + float(token_inr_value)

                    self.dao.update_fiat_bank_balance_by_wallet_address(
                        from_addr,
                        new_balance
                    )
                    tx_hash = tx_hash if isinstance(tx_hash, str) else tx_hash.hex()

                    return {
                        "tx_hash": tx_hash,
                        "status": "confirmed",
                        "type": transfer_type,
                        "old_fiat_bank_balance": cust_balance,
                        "new_fiat_bank_balance": float(new_balance)
                    }
            
            else:
                from Business_Layer.onchain_sepolia_gateway.services.onchain_token_service import (
                    OnchainTokenService,
                )

                from_addr = self.web3.to_checksum_address(req.from_address)
                to_addr = self.web3.to_checksum_address(req.to_address)

                tenant = self.tenant_dao.get_tenant_by_id(tenant_id)
                token_config = self.token_dao.get_token_by_symbol(
                    tenant_id,
                    asset
                )

                if not token_config:
                    raise HTTPException(
                        400,
                        f"{asset} not configured for tenant"
                    )

                private_key = self.dao.get_private_key_by_address(from_addr)
                if not private_key:
                    raise HTTPException(404, "Wallet not found")

                token_service = OnchainTokenService()
                token_service.configure(
                    tenant.rpc_url,
                    token_config.contract_address,
                    private_key,
                    tenant.chain_id
                )

                # Balance check
                balance = token_service.get_balance(from_addr)
                decimals = token_config.decimals or 18
                token_amount = Decimal(str(req.amount))
                amount_units = int(token_amount * (Decimal(10) ** decimals))

                if balance < amount_units:
                    raise HTTPException(400, "Insufficient token balance")

                # Send tx (do NOT wait for receipt)
                tx_hash = token_service.transfer(to_addr, token_amount)
                transfer_type = "Transfer"

            # Invalidate wallet balance cache for both wallets
            self.redis.invalidate_wallet_balance(from_addr.lower())
            self.redis.invalidate_wallet_balance(to_addr.lower())

            logger.info(
                f"🗑️ Wallet balance cache invalidated for {from_addr.lower()} and {to_addr.lower()}"
            )

            return {
                "tx_hash": tx_hash.hex() if not isinstance(tx_hash, str) else tx_hash,
                "status": "confirmed",
                "type": transfer_type
            }

        except HTTPException as he:
            raise he

        except Exception as e:
            raise HTTPException(500, str(e))


    # Contract Resolver
    def _get_contract(self, asset: str):

        if asset == "USDC":
            return self.usdc_contract

        if asset == "USDT":
            return self.usdt_contract

        raise HTTPException(400, "Unsupported asset")

    
    def verify_address(self, address):
        try:
            if not self.web3.is_address(address):
                return False
            return True
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(500, str(e))

    
    
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
            
    