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

    def register_user(self, mail: str, name: str, password: str):
        print("entering service layer", password)
        
        if not self._is_valid_email(mail):
            raise ValueError("Invalid email format.")

        if not self._is_strong_password(password):
            raise ValueError(
                "Password must be at least 8 characters long and contain "
                "uppercase, lowercase, digit, and special character."
            )

        existing_user = self.user_dao.get_user_by_email(mail)
        if existing_user:
            raise ValueError("User with this email already exists.")
        
        # print("password before hashing", password)
        # hashed_password = self._hash_password(password)
        # print("hashed password", hashed_password)
        
        acc = Account.create()
        # print("details", mail, name, hashed_password)
        password = password.strip()

        new_user = self.user_dao.create_user(
            mail=mail,
            name=name,
            password=password,
            wallet_address=acc.address,
            private_key=acc.key.hex()
        )

        return new_user

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

    def update_password(self, user_id: int, new_password: str):
        if not self._is_strong_password(new_password):
            raise ValueError(
                "Password must be at least 8 characters long and contain "
                "uppercase, lowercase, digit, and special character."
            )

        hashed_password = self._hash_password(new_password)

        updated_user = self.user_dao.update_user_password(
            user_id,
            hashed_password
        )

        if not updated_user:
            raise ValueError("User not found.")

        return updated_user

    def update_password_by_mail(self, mail: str, new_password: str):
        if not self._is_strong_password(new_password):
            raise ValueError(
                "Password must be at least 8 characters long and contain "
                "uppercase, lowercase, digit, and special character."
            )

        user = self.user_dao.get_user_by_email(mail)
        if not user:
            raise ValueError("User not found.")

        # hashed_password = self._hash_password(new_password)

        updated_user = self.user_dao.update_user_password(
            user.user_id,
            new_password
        )

        return updated_user
    
    def get_users(self):
        return self.user_dao.get_all_users()

