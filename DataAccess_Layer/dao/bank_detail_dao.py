from typing import Optional
from DataAccess_Layer.models.model import BankCustomerDetails, CustomerPayee
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
    def create_payee(self, id, request):
        new_payee = CustomerPayee(
            customer_id=id,
            payee_name=request.payee_name,
            phone_number=request.phone_number,
            bank_account_number=request.bank_account_number,
            wallet_address=request.wallet_address,
            nickname=request.nickname,
            is_favorite=request.is_favorite,
            is_active=request.is_active
        )
        self.db.add(new_payee)
        self.db.commit()
        self.db.refresh(new_payee)
        return new_payee
    def get_payees(self, customer_id):
        return self.db.query(CustomerPayee).filter_by(customer_id=customer_id).all()
    def get_payee_by_id(self, payee_id):
        return self.db.query(CustomerPayee).filter_by(id=payee_id).first()
    def delete_payee(self, payee_id):
        payee = self.db.query(CustomerPayee).filter_by(id=payee_id).first()
        if not payee:
            return None
        self.db.delete(payee)
        self.db.commit()
        return True