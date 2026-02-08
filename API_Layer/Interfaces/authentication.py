from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    mail: str
    password: str

class LoginResponse(BaseModel):
    id: int
    name: str
    tenant_id: int
    customer_id: str
    phone_number: Optional[str] = None
    is_active: bool
    is_wallet: bool
    wallet_address: Optional[str] = None
    bank_account_number: Optional[str] = None

class Userdetails(BaseModel):
    id: int
    name: str
    mail: str
    tenant_id: int
    customer_id: str
    phone_number: Optional[str] = None
    is_active: bool
    is_wallet: bool
    wallet_address: Optional[str] = None
    bank_account_number: Optional[str] = None
    fiat_bank_balance: Optional[float] = None
    created_at: str

class CreateUserRequest(BaseModel):
    tenant_id: int
    mail: str
    name: str
    password: str
    phone_number: str
    is_active: Optional[bool] = True
class UpdateAdminRequest(BaseModel):
    mail: str
    name: str
    password: str
    phone_number: str
    bank_account_number: str
    is_active: Optional[bool] = True
    fiat_bank_balance: Optional[float] = 0.00

class UpdateUserRequest(BaseModel):
    mail: str
    name: str
    password: str
    phone_number: str
    is_active: Optional[bool] = None

class CreateUserResponse(BaseModel):
    customer_id: str
    message: str

class CreateWalletResponse(BaseModel):
    wallet_address: str
    message: str