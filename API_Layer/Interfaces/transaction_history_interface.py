from pydantic import BaseModel
from typing import Optional
import enum

class EnumStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class EnumTransactionType(str, enum.Enum):
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    CLAIMED = "CLAIMED"  # getting free tokens from tenderly faucet
    BURNED = "BURNED"

class TransactionHistoryResponse(BaseModel):
    from_address: str
    to_address: Optional[str] = None # could be None for CLAIMED type & sender address if Received | receiver address if S
    amount: float
    asset: str
    status: EnumStatus
    tx_hash: Optional[str] = None
    timestamp: Optional[str] = None
    transaction_type: EnumTransactionType