from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Text, DateTime, func, JSON
from sqlalchemy.orm import relationship
from DataAccess_Layer.utils.database import Base

class user_Wallet(Base):
    __tablename__ = "user_wallets"

    user_id = Column(Integer, primary_key=True, index=True)
    mail = Column(String(150), unique=True)
    name = Column(String(100))
    password = Column(String(255))
    is_active = Column(Boolean, default=True)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    private_key = Column(String, nullable=False)