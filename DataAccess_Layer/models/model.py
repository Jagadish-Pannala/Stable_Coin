from sqlalchemy import Column, Integer, Numeric, String, Boolean, ForeignKey, Text, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from DataAccess_Layer.utils.database import Base


# -------------------------------
# Tenant / Organization
# -------------------------------
class TenantDetails(Base):
    __tablename__ = "tenant_details"

    id = Column(Integer, primary_key=True, index=True)
    tenant_name = Column(String(100), nullable=False)
    rpc_url = Column(String(200), nullable=False)
    chain_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customers = relationship("BankCustomerDetails", back_populates="tenant", cascade="all, delete")

    __table_args__ = (
        Index("idx_tenant_active", "is_active"),
    )


# -------------------------------
# Bank Customers
# -------------------------------
class BankCustomerDetails(Base):
    __tablename__ = "bank_customer_details"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant_details.id", ondelete="CASCADE"), nullable=False)

    customer_id = Column(String(50), nullable=False)
    mail = Column(String(150), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    phone_number = Column(String(15))
    bank_account_number = Column(String(30))

    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    wallet_address = Column(String(255), unique=True, index=True)
    private_key = Column(Text)

    is_wallet = Column(Boolean, default=False)

    fiat_balance = Column(Numeric(18, 2), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("TenantDetails", back_populates="customers")
    payer_mappings = relationship("CustomerPayerMapping", back_populates="customer", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="unique_tenant_customer"),
        Index("idx_customer_tenant", "tenant_id"),
        Index("idx_customer_active", "is_active"),
        Index("idx_customer_wallet", "wallet_address"),
    )


# -------------------------------
# Payer Details
# -------------------------------
class PayerDetails(Base):
    __tablename__ = "payer_details"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone_number = Column(String(15), nullable=False)
    wallet_address = Column(String(255), unique=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer_mappings = relationship("CustomerPayerMapping", back_populates="payer", cascade="all, delete")

    __table_args__ = (
        Index("idx_payer_wallet", "wallet_address"),
    )


# -------------------------------
# Customer - Payer Mapping
# -------------------------------
class CustomerPayerMapping(Base):
    __tablename__ = "customer_payer_mapping"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("bank_customer_details.id", ondelete="CASCADE"), nullable=False)
    payer_id = Column(Integer, ForeignKey("payer_details.id", ondelete="CASCADE"), nullable=False)

    relationship_type = Column(String(50))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("BankCustomerDetails", back_populates="payer_mappings")
    payer = relationship("PayerDetails", back_populates="customer_mappings")

    __table_args__ = (
        UniqueConstraint("user_id", "payer_id", name="unique_customer_payer"),
        Index("idx_mapping_user", "user_id"),
        Index("idx_mapping_payer", "payer_id"),
    )
