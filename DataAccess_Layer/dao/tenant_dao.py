from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime

from DataAccess_Layer.models.model import TenantDetails


class TenantDAO:
    def __init__(self, db: Session):
        self.db = db

    # -----------------------------
    # Create Tenant
    # -----------------------------
    def create_tenant(
        self,
        tenant_name: str,
        rpc_url: str,
        chain_id: int
    ) -> TenantDetails:

        tenant = TenantDetails(
            tenant_name=tenant_name,
            rpc_url=rpc_url,
            chain_id=chain_id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    # -----------------------------
    # Get tenant by ID
    # -----------------------------
    def get_tenant_by_id(self, tenant_id: int) -> Optional[TenantDetails]:

        return (
            self.db.query(TenantDetails)
            .filter(
                TenantDetails.id == tenant_id,
                TenantDetails.is_active == True
            )
            .first()
        )

    # -----------------------------
    # Get tenant by name
    # -----------------------------
    def get_tenant_by_name(self, tenant_name: str) -> Optional[TenantDetails]:

        return (
            self.db.query(TenantDetails)
            .filter(
                TenantDetails.tenant_name == tenant_name,
                TenantDetails.is_active == True
            )
            .first()
        )

    # -----------------------------
    # Update tenant
    # -----------------------------
    def update_tenant(
        self,
        tenant_id: int,
        **kwargs
    ) -> Optional[TenantDetails]:

        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    # -----------------------------
    # Soft delete tenant
    # -----------------------------
    def deactivate_tenant(self, tenant_id: int) -> bool:

        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False

        tenant.is_active = False
        tenant.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    # -----------------------------
    # Get all active tenants
    # -----------------------------
    def get_all_tenants(self) -> List[TenantDetails]:

        return (
            self.db.query(TenantDetails)
            .filter(TenantDetails.is_active == True)
            .all()
        )

    # -----------------------------
    # Check tenant has tokens or not
    # -----------------------------
    def tenant_has_tokens(self, tenant_id: int) -> bool:

        tenant = (
            self.db.query(TenantDetails)
            .options(joinedload(TenantDetails.tokens))
            .filter(
                TenantDetails.id == tenant_id,
                TenantDetails.is_active == True
            )
            .first()
        )

        return bool(tenant and tenant.tokens)

    # -----------------------------
    # Get tenant with tokens
    # -----------------------------
    def get_tenant_with_tokens(
        self,
        tenant_id: int
    ) -> Optional[TenantDetails]:

        return (
            self.db.query(TenantDetails)
            .options(joinedload(TenantDetails.tokens))
            .filter(
                TenantDetails.id == tenant_id,
                TenantDetails.is_active == True
            )
            .first()
        )
