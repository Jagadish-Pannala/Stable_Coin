import random
from decimal import Decimal
import re
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from utils.web3_client import Web3Client
import os
from dotenv import load_dotenv
# import bcrypt
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
from DataAccess_Layer.dao.wallet_dao import WalletDAO
from DataAccess_Layer.utils.database import set_db_session, remove_db_session
from eth_account import Account
from API_Layer.Interfaces.wallet_interface import FaucetRequest
from web3 import Web3
from DataAccess_Layer.dao.tenant_dao import TenantDAO


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationService:
    def __init__(self,db: Session):
        self.web3 = Web3Client().w3
        self.db = db
        self.user_dao = UserAuthDAO(self.db)
        self.wallet_dao = WalletDAO(self.db)
        self.tenant_dao = TenantDAO(self.db)

    def __del__(self):
        remove_db_session()

    # ------------------ helpers ------------------

    def _is_valid_email(self, mail: str) -> bool:
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return bool(re.match(email_regex, mail))

    def _is_strong_password(self, password: str) -> bool:
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"[0-9]", password):
            return False
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False
        return True

    
 
    # def _hash_password(self, password: str) -> str:
    #     """Hash password using bcrypt"""
    #     salt = bcrypt.gensalt(rounds=12)  # 12 rounds is a good balance
    #     hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    #     return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        # result = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        # if not result:
        #     print("Password verification failed")
        #     return False
        # return True

        return password.strip() == hashed.strip()
    def generate_customer_id(self, tenant_id: int) -> str:
        """
        Generate next customer_id like CUST1712 based on last ID for tenant.
        """

        # Get last customer for tenant
        last_customer = self.user_dao.get_last_customer_id(tenant_id)

        print("Last customer:", last_customer)

        if not last_customer or not last_customer[0]:
            # First customer for tenant
            return "CUST1701"

        last_customer_id = last_customer[0]

        print("Last customer_id:", last_customer_id)

        # Extract number from CUSTXXXX
        match = re.search(r"(\d+)$", last_customer_id)

        if not match:
            raise ValueError(f"Invalid customer_id format: {last_customer_id}")

        last_number = int(match.group(1))

        next_number = last_number + 1

        new_customer_id = f"CUST{next_number}"

        return new_customer_id
    def generate_bank_account_number(self) -> str:
        prefix = "1711"
        random_part = ''.join(str(random.randint(0, 9)) for _ in range(8))
        return prefix + random_part



    def create_user(self, tenant_id, mail, name, password, phone_number, is_active=True, fiat_bank_balance=0.00):
        try:
            customer_id = self.generate_customer_id(tenant_id)
            bank_account_number = self.generate_bank_account_number()
            print(f"Generated customer_id: {customer_id}, bank_account_number: {bank_account_number}")
            existing_customer = self.user_dao.checking_customer_existing(customer_id, tenant_id, phone_number)
            if existing_customer:
                raise HTTPException(
                    status_code=400,
                    detail="Customer ID already exists for this tenant or phone number already registered"
                )
            if not self._is_valid_email(mail):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid email format"
                )
            if not self._is_strong_password(password):
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 8 characters long and include uppercase letters, lowercase letters, numbers, and special characters"
                )
            # hashed_password = self._hash_password(password)
            hashed_password = password
            user = self.user_dao.create_user(
                tenant_id=tenant_id,
                customer_id=customer_id,
                mail=mail,
                name=name,
                password=hashed_password,
                phone_number=phone_number,
                bank_account_number=bank_account_number,
                is_active=is_active,
                is_wallet=False,
                fiat_bank_balance=fiat_bank_balance
            )
            return customer_id
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        
    
    def create_wallet_for_user(self, request):
        try:
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

            account = Account.create()
            wallet_address = account.address
            encrypted_private_key = account.key.hex()

            
            print('address', wallet_address)
            print('encrypted_private_key', encrypted_private_key)
            wallet_address = self.web3.to_checksum_address(wallet_address)
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
            result = self.add_eth_wallet_creation(wallet_address, amount, main_wallet,rpc)
            result = self.user_dao.create_wallet_for_user(
                request.customer_id,
                request.tenant_id,
                wallet_address,
                encrypted_private_key
            )
            return wallet_address

            # # ✅ Lazy import to avoid circular dependency
            # from Business_Layer.wallet_service import WalletService

            # wallet_service = WalletService(self.db)

            # faucet_request = FaucetRequest(
            #     address=wallet_address,
            #     type="ETH",
            #     amount=1
            # )

            # wallet_service.create_free_tokens(faucet_request)

            # return result

        except HTTPException as he:
            raise he

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    def authenticate_user(self, mail, password):
        try:
            user = self.user_dao.get_user_by_email(mail)

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            if not self._verify_password(password, user.password):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid password"
                )

            return user
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

        
    def get_users(self):
        return self.user_dao.get_all_users()
    

    def add_eth_wallet_creation(self, to_address, amount, main_wallet, rpc):

        # Create Web3 instance using provided RPC
        web3 = Web3(Web3.HTTPProvider(rpc))
        print("rpc:", rpc)

        if not web3.is_connected():
            raise Exception("RPC connection failed")
        
        print(main_wallet)

        # Get private key from DB
        private_key = self.wallet_dao.get_private_key_by_address(main_wallet)

        # Nonce from RPC network
        nonce = web3.eth.get_transaction_count(main_wallet, "pending")

        tx = {
            "from": main_wallet,
            "to": Web3.to_checksum_address(to_address),
            "value": web3.to_wei(amount, "ether"),
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
            "gasPrice": web3.eth.gas_price,
            "gas": 21000
        }

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)

        raw_tx = (
            signed_tx.raw_transaction
            if hasattr(signed_tx, "raw_transaction")
            else signed_tx.rawTransaction
        )

        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        print("Transaction sent with hash:", tx_hash.hex())
        return web3.to_hex(tx_hash)

            

