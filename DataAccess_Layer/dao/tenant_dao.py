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
        request
    ):

        tenant = TenantDetails(
            tenant_name=request.tenant_name,
            rpc_url=request.rpc_url,
            chain_id=request.chain_id,
            is_active=request.is_active,
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
    
    def get_tenant_by_id_only(self, tenant_id: int) -> Optional[TenantDetails]:

        return (
            self.db.query(TenantDetails)
            .filter(
                TenantDetails.id == tenant_id
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
        tenant_id, request):

        tenant = self.get_tenant_by_id_only(tenant_id)
        if not tenant:
            return False

        tenant.tenant_name = request.tenant_name
        tenant.rpc_url = request.rpc_url
        tenant.chain_id = request.chain_id
        tenant.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    # -----------------------------
    # Soft delete tenant
    # -----------------------------
    def deactivate_tenant(self, tenant_id, is_active):

        tenant = self.get_tenant_by_id_only(tenant_id)
        if not tenant:
            return False

        tenant.is_active = is_active
        tenant.updated_at = datetime.utcnow()
        self.db.commit()
        return tenant

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
    
    def get_rpc_by_tenant_id(self, tenant_id: int) -> Optional[str]:

        tenant = self.get_tenant_by_id(tenant_id)
        if tenant:
            return tenant.rpc_url
        return None
