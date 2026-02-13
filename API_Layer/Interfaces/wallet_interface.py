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

class AssetType(str, enum.Enum):
    ETH = "ETH"
    USDC = "USDC"
    USDT = "USDT"

class FaucetRequest(BaseModel):
    address: str
    type: AssetType
    amount: Optional[float] = 1.0

class FaucetResponse(BaseModel):
    success: bool
    tx_hash: str
    message: str
    fiat_bank_balance: Optional[float] = None
    

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
    # balance_eth: float
    balance_usdc: float
    balance_usdt: float

class FiatBalanceResponse(BaseModel):
    bank_account_number: str
    fiat_bank_balance: float
class StablecoinBalance(BaseModel):
    symbol: str
    balance: float

class BalResponse(BaseModel):
    totalFiat: float
    stablecoins: list[StablecoinBalance]
    totalStablecoinValue: float

class SearchResponse(BaseModel):
    customer_id: str
    name: str
    phone_number: Optional[str] = None
    wallet_address: str
class SearchUsersRequest(BaseModel):
    query: str
    tenant_id: int
    current_customer_id: str

