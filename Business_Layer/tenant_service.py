from fastapi import HTTPException
from DataAccess_Layer.dao.tenant_dao import TenantDAO


class TenantService:
    def __init__(self, db=None):
        self.db = db
        self.dao = TenantDAO(self.db)
    def get_all_tenants(self):
        try:
            return self.dao.get_all_tenants()
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_tenant_by_id(self, tenant_id):
        try:
            result =  self.dao.get_tenant_by_id_only(tenant_id)
            if not result:
                raise HTTPException(status_code=404, detail="Tenant not found")
            return result
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    def create_tenant(self, request):
        try:
            result = self.dao.create_tenant(request)
            return result.id
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def update_tenant(self, tenant_id, request):
        try:
            tenant = self.get_tenant_by_id(tenant_id)
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            return self.dao.update_tenant(tenant_id, request)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    def deactivate_tenant(self, request):
        try:
            tenant = self.get_tenant_by_id(request.tenant_id)
            print("IN Service", tenant)
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            return self.dao.deactivate_tenant(request.tenant_id, request.is_active)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))