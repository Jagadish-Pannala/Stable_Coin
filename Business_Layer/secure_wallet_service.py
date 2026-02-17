from fastapi import HTTPException
from eth_account import Account
from mnemonic import Mnemonic
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
import json

class SecureWalletManager:
    def __init__(self, db=None):
        self.db = db
        self.user_dao = UserAuthDAO(self.db)

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

            self.user_dao.create_wallet_for_user(request.customer_id, request.tenant_id, account.address, keystore_json)

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
