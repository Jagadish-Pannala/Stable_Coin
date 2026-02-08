from sqlalchemy.orm import Session
from DataAccess_Layer.models.model import BankCustomerDetails, CustomerPayee
from typing import Optional, List ,Tuple

class WalletDAO:
    def __init__(self, db):
        self.db = db

    def get_private_key_by_address(self, address: str) -> Optional[str]:
        user = self.db.query(BankCustomerDetails).filter_by(wallet_address=address).first()
        if user:
            return user.encrypted_private_key
        return None
    def get_all_users(self):
        user = self.db.query(BankCustomerDetails.customer_id, BankCustomerDetails.mail, BankCustomerDetails.wallet_address).all()
        return user

    def get_fiat_balance_by_customer_id(
        self, customer_id: str
    ) -> Optional[Tuple[str, float]]:
        user = (
            self.db.query(BankCustomerDetails)
            .filter(BankCustomerDetails.customer_id == customer_id)
            .first()
        )
        if not user:
            return None
        return user.bank_account_number, user.fiat_bank_balance
    
    def get_fiat_bank_balance_by_wallet_address(self, wallet_address: str) -> Optional[float]:
        user = self.db.query(BankCustomerDetails).filter_by(wallet_address=wallet_address).first()
        if user:
            return user.fiat_bank_balance
        return 0.0
    
    def update_fiat_bank_balance_by_wallet_address(self, wallet_address: str, new_balance:float):
        user = self.db.query(BankCustomerDetails).filter_by(wallet_address=wallet_address).first()
        if not user:
            return None
        user.fiat_bank_balance = new_balance
        self.db.commit()
        self.db.refresh(user)
        return user.fiat_bank_balance

    def update_admin_fiat_bank_balance(self, amount: float):
        admin = self.db.query(BankCustomerDetails).filter_by(tenant_id=1, customer_id="ADMI1711").first()
        if not admin:
            return None
        admin.fiat_bank_balance += amount
        self.db.commit()
        self.db.refresh(admin)
        return admin.fiat_bank_balance
    
    def get_users_by_search_query(self, query: str) -> List[BankCustomerDetails]:
        search_pattern = f"%{query}%"
        users = self.db.query(BankCustomerDetails).filter(
            (BankCustomerDetails.name.ilike(search_pattern)) |
            (BankCustomerDetails.phone_number.ilike(search_pattern)) |
            (BankCustomerDetails.wallet_address.ilike(search_pattern))
        ).all()
        return users
    # check payees for particular customer and return results
    
    def search_payees_for_customer(self, customer_id: str, query: str) -> list[CustomerPayee]:
        search_pattern = f"%{query}%"

        return (
            self.db.query(CustomerPayee)
            .filter(
                CustomerPayee.customer_id == customer_id,
                (
                    CustomerPayee.payee_name.ilike(search_pattern) |
                    CustomerPayee.wallet_address.ilike(search_pattern) |
                    CustomerPayee.phone_number.ilike(search_pattern)
                )
            )
            .all()
        )
