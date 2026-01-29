from sqlalchemy.orm import Session
from DataAccess_Layer.models.model import user_Wallet
from typing import Optional, List

class WalletDAO:
    def __init__(self, db):
        self.db = db
    def get_private_key_by_address(self, address: str) -> Optional[str]:
        user = self.db.query(user_Wallet).filter_by(wallet_address=address).first()
        if user:
            return user.private_key
        return None