
from openai import models
from sqlalchemy.orm import Session
from DataAccess_Layer.models.model import user_Wallet
from typing import Optional, List


import logging

logger = logging.getLogger(__name__)

class UserAuthDAO:
    """Data Access Object for User Authentication operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[user_Wallet]:
        return self.db.query(user_Wallet).filter_by(mail=email).first()

    def get_user_by_id(self, user_id: int) -> Optional[user_Wallet]:
        return self.db.query(user_Wallet).filter_by(user_id=user_id).first()
    
    def count_users(self) -> int:
        return self.db.query(user_Wallet).count()
    
    def count_active_users(self) -> int:
        return self.db.query(user_Wallet).filter(user_Wallet.is_active == True).count()

    def get_all_users(self) -> List[user_Wallet]:
        return self.db.query(user_Wallet).all()

    def create_user(self, mail: str, name: str, password: str, wallet_address: str, private_key: str) -> user_Wallet:
        new_user = user_Wallet(
            mail=mail,
            name=name,
            password=password,
            wallet_address=wallet_address,
            private_key=private_key,
            is_active=True
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user
    
    def update_user(self, user_id: int, **kwargs) -> Optional[user_Wallet]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user_password(self, user_id: int, new_password: str) -> Optional[user_Wallet]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        user.password = new_password
        self.db.commit()
        self.db.refresh(user)
        return user