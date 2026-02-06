import random
import re
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
# import bcrypt
from DataAccess_Layer.dao.user_authentication import UserAuthDAO
from DataAccess_Layer.utils.database import set_db_session, remove_db_session
from eth_account import Account


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationService:
    def __init__(self,db: Session):
        self.db = db
        self.user_dao = UserAuthDAO(self.db)

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
        
    
    def create_wallet_for_user(self, customer_id):
        try:
            user = self.user_dao.get_user_by_customer_id(customer_id)
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
            encrypted_private_key = account.key.hex()  # In production, encrypt this key and store securely
            result = self.user_dao.create_wallet_for_user(customer_id, wallet_address, encrypted_private_key)
            return result
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

