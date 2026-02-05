from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    mail: str
    password: str

class LoginResponse(BaseModel):
    id: int
    name: str
    tenant_id: int
    customer_id: int
    phone_number: Optional[str] = None
    is_active: bool
    is_wallet: bool
    wallet_address: Optional[str] = None
    bank_account_number: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str
    password: str
    email: str

class RegisterResponse(BaseModel):
    success: bool
    userid: Optional[int] = None
    message: str

class UpdatePasswordRequest(BaseModel):
    email: str
    new_password: str

class UpdatePasswordResponse(BaseModel):
    success: bool
    message: str