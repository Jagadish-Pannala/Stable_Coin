from sqlalchemy.orm import Session
from DataAccess_Layer.models.model import BankCustomerDetails
from typing import Optional, List

class WalletDAO:
    def __init__(self, db):
        self.db = db
    def get_private_key_by_address(self, address: str) -> Optional[str]:
        user = self.db.query(BankCustomerDetails).filter_by(wallet_address=address).first()
        if user:
            return user.private_key
        return None
    def get_all_users(self):
        user = self.db.query(BankCustomerDetails.customer_id, BankCustomerDetails.mail, BankCustomerDetails.wallet_address).all()
        return user