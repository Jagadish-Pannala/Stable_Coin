from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    username: str
    success: bool
    userid: Optional[int] = None
    message: str
    wallet_address: Optional[str] = None

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
    old_password: str
    new_password: str

class UpdatePasswordResponse(BaseModel):
    success: bool
    message: str