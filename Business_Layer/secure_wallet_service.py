from decimal import Decimal
from fastapi import HTTPException
from eth_account import Account
from mnemonic import Mnemonic
from Business_Layer.authentication_service import AuthenticationService
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
import json

from DataAccess_Layer.dao.tenant_dao import TenantDAO
from DataAccess_Layer.dao.wallet_dao import WalletDAO
from utils.web3_client import Web3Client

from web3 import Web3

class SecureWalletManager:
    def __init__(self, db=None):
        self.web3 = Web3Client().w3
        self.db = db
        self.user_dao = UserAuthDAO(self.db)
        self.wallet_dao = WalletDAO(self.db)
        self.tenant_dao = TenantDAO(self.db)
        self.auth_dao = AuthenticationService(self.db)

    def create_wallet_with_mnemonic(self, request, strength=256):
        try:
            Account.enable_unaudited_hdwallet_features()

            mnemo = Mnemonic("english")
            mnemonic = mnemo.generate(strength=strength)

            account = Account.from_mnemonic(
                mnemonic,
                account_path="m/44'/60'/0'/0/0"
            )
            user = self.user_dao.get_user_by_customer_id_tenant_id(request.customer_id, request.tenant_id)

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )

            if user.is_wallet:
                raise HTTPException(
                    status_code=400,
                    detail="User already has a wallet"
                )


            # Encrypt immediately
            encrypted_keystore = account.encrypt(user.password)

            keystore_json = json.dumps(encrypted_keystore)
            
            wallet_address = self.web3.to_checksum_address(account.address)
            amount = Decimal(str(1))
            main_wallet = self.user_dao.get_main_wallet_address(request.tenant_id)
            if not main_wallet:
                raise HTTPException(
                    status_code=500,
                    detail="Main wallet not found for tenant"
                )
            rpc = self.tenant_dao.get_rpc_by_tenant_id(request.tenant_id)
            if not rpc:
                raise HTTPException(
                    status_code=500,
                    detail="RPC URL not found for tenant"
                )
            print("Main wallet:", main_wallet)
            if request.tenant_id == 2:
                amount = Decimal(str(0.01))
                # Connect to tenant RPC
                web3_rpc = Web3(Web3.HTTPProvider(rpc))

                # Get main wallet ETH balance
                balance_wei = web3_rpc.eth.get_balance(main_wallet)
                balance_eth = Decimal(web3_rpc.from_wei(balance_wei, "ether"))

                # Prevent central wallet going below 28 ETH
                if balance_eth - amount < Decimal("28"):
                    raise HTTPException(
                        status_code=400,
                        detail="Unable to create wallet: central wallet ETH balance too low"
                    )
            
            self.user_dao.create_wallet_for_user(
                request.customer_id,
                request.tenant_id,
                account.address,
                keystore_json
            )
            self.auth_dao.add_eth_wallet_creation(account.address, amount, main_wallet,rpc,tenant_id=request.tenant_id)
            

            return account.address

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    




# class SecureWalletManager:
#     def __init__(self, db=None):
#         self.db = db
#     def create_wallet_with_mnemonic(self, strength=256):
#         try:
#             print("entering create wallet mnemonic in service layer")
#             """Create wallet with seed phrase (24 words)"""
#             Account.enable_unaudited_hdwallet_features()
            
#             mnemo = Mnemonic("english")
#             mnemonic = mnemo.generate(strength=strength)
            
#             account = Account.from_mnemonic(
#                 mnemonic,
#                 account_path="m/44'/60'/0'/0/0"
#             )
            
#             return {
#                 "address": account.address,
#                 "private_key": account.key.hex(),  # if you really want to return it
#                 "mnemonic": mnemonic
#             }

#         except HTTPException as he:
#             raise he
#         except Exception as e:
#             raise HTTPException(
#                 status_code=500,
#                 detail=str(e)
#             )
#     def encrypt_account(self, account: Account, password: str) -> dict:
#         """Encrypt account using eth_account's built-in encryption"""
#         # This uses the Web3 Secret Storage Definition (scrypt-based)
#         encrypted_keystore = account.encrypt(password)
#         return encrypted_keystore
    
#     def decrypt_account(self, encrypted_keystore: dict, password: str) -> Account:
#         """Decrypt and restore account"""
#         private_key = Account.decrypt(encrypted_keystore, password)
#         return Account.from_key(private_key)
