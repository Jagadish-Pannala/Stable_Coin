from pydantic import BaseModel

class Create_Tenet_Request(BaseModel):
    name: str
    is_active: bool