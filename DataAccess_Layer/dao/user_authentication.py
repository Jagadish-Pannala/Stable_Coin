
from sqlalchemy.orm import Session
from DataAccess_Layer.models.model import BankCustomerDetails
from typing import Optional, List
from sqlalchemy import desc

import logging

logger = logging.getLogger(__name__)

class UserAuthDAO:
    """Data Access Object for User Authentication operations"""

    def __init__(self, db: Session):
        self.db = db
    def get_last_customer_id(self, tenant_id):
        query = (
            self.db.query(BankCustomerDetails.customer_id)
            .filter(BankCustomerDetails.tenant_id == tenant_id)
            .order_by(desc(BankCustomerDetails.id))
            .first()
        )
        return query if query else None
    def get_user_by_email(self, email: str):
        return self.db.query(BankCustomerDetails).filter_by(mail=email).first()

    def get_user_by_customer_id(self, customer_id: str) -> Optional[BankCustomerDetails]:
        return self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id).first()
    
    def checking_customer_existing(self, customer_id, tenant_id, phone_number):
        return self.db.query(BankCustomerDetails).filter(
            BankCustomerDetails.tenant_id == tenant_id,
            (
                (BankCustomerDetails.customer_id == customer_id) |
                (BankCustomerDetails.phone_number == phone_number)
            )
        ).first()

    # def checking_user_by_customer_id(self, customer_id):
    #     result = self.db.query(BankCustomerDetails.is_wallet).filter_by(customer_id=customer_id).first()
    #     return result if result else None
        
    def count_users(self) -> int:
        return self.db.query(BankCustomerDetails).count()
    
    def count_active_users(self) -> int:
        return self.db.query(BankCustomerDetails).filter(BankCustomerDetails.is_active == True).count()

    def get_all_users(self) -> List[BankCustomerDetails]:
        return self.db.query(BankCustomerDetails).all()

    def create_user(self, tenant_id, customer_id, mail, name, password, phone_number, bank_account_number, is_active=True, is_wallet=False, fiat_bank_balance=0.00) -> BankCustomerDetails:
        new_user = BankCustomerDetails(
            tenant_id=tenant_id,
            customer_id=customer_id,
            mail=mail,
            name=name,
            password=password,
            phone_number=phone_number,
            bank_account_number=bank_account_number,
            is_active=is_active,
            is_wallet=is_wallet,
            fiat_bank_balance=fiat_bank_balance
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return True
    def create_wallet_for_user(self, customer_id, wallet_address, encrypted_private_key):
        user = self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id).first()
        if not user:
            return None
        user.wallet_address = wallet_address
        user.encrypted_private_key = encrypted_private_key
        user.is_wallet = True
        self.db.commit()
        self.db.refresh(user)
        return wallet_address
    
    def update_user(self, user_id: int, **kwargs) -> Optional[BankCustomerDetails]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user_password(self, user_id: int, new_password: str) -> Optional[BankCustomerDetails]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        user.password = new_password
        self.db.commit()
        self.db.refresh(user)
        return user