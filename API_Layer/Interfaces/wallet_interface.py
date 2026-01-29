from pydantic import BaseModel
from typing import Optional
import enum

class WalletAddress(BaseModel):
    address: str

class CreateWalletResponse(BaseModel):
    success: bool
    address: str
    private_key: str
    message: str

class FaucetRequest(BaseModel):
    address: str
    type:Optional[str] = "ETH"
    amount: Optional[float] = 1.0

class FaucetResponse(BaseModel):
    success: bool
    tx_hash: str
    message: str

class VerifyAddressResponse(BaseModel):
    address: str
    is_valid: bool

class TransferRequest(BaseModel):
    from_address: str
    to_address: str
    amount: float
    asset: Optional[str] = "ETH"

class BalanceResponse(BaseModel):
    address: str
    balance_wei: int
    balance_eth: float
    balance_usdc: float

