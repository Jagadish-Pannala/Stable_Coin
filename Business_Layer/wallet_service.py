from eth_account import Account
from fastapi import HTTPException
from web3 import Web3
from utils.web3_client import Web3Client
from storage.wallet_repository import WalletRepository
from API_Layer.Interfaces.wallet_interface import BalanceResponse, TransferRequest

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"},
                                   {"name": "_value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "success", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

class WalletService:
    def __init__(self):
        self.web3 = Web3Client().w3
        self.repo = WalletRepository()

        self.usdc_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(
                "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
            ),
            abi=ERC20_ABI
        )

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
            balance_wei=balance_wei,
            balance_eth=float(balance_eth),
            balance_usdc=float(usdc)
        )
    def list_wallets(self):
        """
        List all wallets stored in wallets.json
        (private keys are NEVER exposed)
        """
        try:
            wallets = self.repo.load()
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
                    "address": w["address"],
                    "created_at": w.get("created_at", "unknown"),
                    "balance_eth": eth_balance,
                    "balance_usdc": float(usdc_balance)
                })

            return {
                "total_wallets": len(safe_wallets),
                "wallets": safe_wallets
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    def transfer(self, req: TransferRequest):
        from_addr = self.web3.to_checksum_address(req.from_address)
        to_addr = self.web3.to_checksum_address(req.to_address)

        account = Account.from_key(req.private_key)
        if account.address != from_addr:
            raise HTTPException(400, "Private key mismatch")

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

        signed = self.web3.eth.account.sign_transaction(tx, req.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)

        return {"tx_hash": tx_hash.hex(), "status": "submitted"}
