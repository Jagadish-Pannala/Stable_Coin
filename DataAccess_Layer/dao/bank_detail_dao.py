from typing import Optional
from DataAccess_Layer.models.model import BankCustomerDetails
from sqlalchemy.orm import Session

class BankDetailDAO:
    """Data Access Object for Bank Customer Details"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_customer_id(self, customer_id: str) -> BankCustomerDetails:
        return self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id).first()
    def get_user_by_customer_id_and_tenant_id(self, customer_id: str, tenant_id: str) -> Optional[BankCustomerDetails]:
        return self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id, tenant_id=tenant_id).first()
    def update_user_details(self, customer_id, request):
        user = self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id).first()
        if not user:
            return None
        user.mail = request.mail
        user.name = request.name
        user.password = request.password
        user.phone_number = request.phone_number
        user.bank_account_number = request.bank_account_number
        self.db.commit()
        self.db.refresh(user)
        return True
    def admin_update_user_details(self, customer_id, request):
        user = self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id).first()
        if not user:
            return None
        user.mail = request.mail
        user.name = request.name
        user.password = request.password
        user.phone_number = request.phone_number
        user.bank_account_number = request.bank_account_number
        user.is_active = request.is_active if request.is_active is not None else user.is_active
        user.fiat_bank_balance = request.fiat_bank_balance if request.fiat_bank_balance is not None else user.fiat_bank_balance
        
        self.db.commit()
        self.db.refresh(user)
        return True
    def add_fiat_balance(self, tenant_id,customer_id, fiat_balance):
        user = self.db.query(BankCustomerDetails).filter_by(customer_id=customer_id, tenant_id=tenant_id).first()
        if not user:
            return None
        user.fiat_bank_balance = (user.fiat_bank_balance or 0) + fiat_balance
        self.db.commit()
        self.db.refresh(user)
        return user.fiat_bank_balance