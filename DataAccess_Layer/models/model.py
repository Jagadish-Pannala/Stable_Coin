from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    DateTime, Text, DECIMAL, Enum,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from DataAccess_Layer.utils.database import Base


# ----------------------------------
# Tenant Details
# ----------------------------------
class TenantDetails(Base):
    __tablename__ = "tenant_details"

    id = Column(Integer, primary_key=True, index=True)
    tenant_name = Column(String(100), nullable=False, unique=True)
    rpc_url = Column(String(200), nullable=False)
    chain_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customers = relationship("BankCustomerDetails", back_populates="tenant", cascade="all, delete")

    __table_args__ = (
        Index("idx_tenant_active", "is_active"),
    )


# ----------------------------------
# Bank Customer Details
# ----------------------------------
class BankCustomerDetails(Base):
    __tablename__ = "bank_customer_details"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant_details.id", ondelete="CASCADE"), nullable=False)

    customer_id = Column(String(50), nullable=False)
    mail = Column(String(150), nullable=False)
    name = Column(String(100), nullable=False)

    phone_number = Column(String(15))
    bank_account_number = Column(String(30))

    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    wallet_address = Column(String(255))
    encrypted_private_key = Column(Text)

    fiat_bank_balance = Column(DECIMAL(18, 2), default=0.00)
    is_wallet = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("TenantDetails", back_populates="customers")
    payees = relationship("CustomerPayee", back_populates="customer", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="unique_tenant_customer_id"),
        UniqueConstraint("tenant_id", "mail", name="unique_tenant_mail"),
        UniqueConstraint("tenant_id", "phone_number", name="unique_tenant_phone"),
        UniqueConstraint("tenant_id", "bank_account_number", name="unique_tenant_bank_account"),
        UniqueConstraint("tenant_id", "wallet_address", name="unique_tenant_wallet"),

        Index("idx_customer_tenant", "tenant_id"),
        Index("idx_customer_active", "is_active"),
        Index("idx_customer_mail", "mail"),
        Index("idx_customer_phone", "phone_number"),
        Index("idx_customer_wallet", "wallet_address"),
        Index("idx_customer_bank_account", "bank_account_number"),
    )


# ----------------------------------
# Customer Payees (Beneficiaries)
# ----------------------------------
class CustomerPayee(Base):
    __tablename__ = "customer_payees"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(Integer, ForeignKey("bank_customer_details.id", ondelete="CASCADE"))

    payee_name = Column(String(100), nullable=False)
    phone_number = Column(String(15), nullable=False)
    bank_account_number = Column(String(30))

    wallet_address = Column(String(255), nullable=False)

    nickname = Column(String(100))
    notes = Column(Text)

    is_favorite = Column(Boolean, default=False)
    relationship_type = Column(String(50))

    payee_type = Column(Enum("internal", "external"), default="external")

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("BankCustomerDetails", back_populates="payees")

    __table_args__ = (
        UniqueConstraint("customer_id", "wallet_address", name="unique_customer_wallet"),

        Index("idx_payee_customer", "customer_id"),
        Index("idx_payee_wallet", "wallet_address"),
        Index("idx_payee_active", "is_active"),
        Index("idx_payee_favorite", "customer_id", "is_favorite"),
    )
