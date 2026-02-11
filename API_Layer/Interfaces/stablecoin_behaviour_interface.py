from pydantic import BaseModel, Field
from enum import Enum

# --------------------------------------------------
# Token Type Enum (Dropdown in Swagger UI)
# --------------------------------------------------
class TokenType(str, Enum):
    USDT = "USDT"
    USDC = "USDC"
    CUSTOM = "CUSTOM"


# --------------------------------------------------
# Request Model
# --------------------------------------------------
class TokenActionRequest(BaseModel):
    tenant_id: int = Field(..., example=1)
    amount: float = Field(..., gt=0, example=10)