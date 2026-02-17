from fastapi import HTTPException
# from Business_Layer.secure_wallet_service import SecureWalletManager
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
from eth_account import Account
import json



def decrypt_password(customer_id, tenant_id, db):
    user_dao = UserAuthDAO(db)
    user = user_dao.get_user_by_customer_id_tenant_id(customer_id, tenant_id)
    print("User retrieved for decryption:", user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_wallet:
        raise HTTPException(status_code=400, detail="User does not have a wallet")
    password = user.password
    keystore_dict = user.encrypted_private_key
    account = Account.from_key(
        Account.decrypt(keystore_dict, password)
    )
    print()
    return account.key.hex()
