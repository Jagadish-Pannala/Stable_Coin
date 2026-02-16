from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Create_Tenant_Request(BaseModel):
    tenant_name: str
    rpc_url: str
    chain_id: int
    is_active: Optional[bool] = True
class Create_Tenant_Response(BaseModel):
    tenant_id: int
    message: str
class Is_Tenant_Active(BaseModel):
    tenant_id: int
    is_active: Optional[bool] = True
class Get_Tenant_Response(BaseModel):
    id: int
    tenant_name: str
    rpc_url: str
    chain_id: int
    is_active: bool