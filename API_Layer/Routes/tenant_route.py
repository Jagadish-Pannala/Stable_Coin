from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from DataAccess_Layer.utils.session import get_db
from Business_Layer.tenant_service import TenantService
from API_Layer.Interfaces.tenant_interface import (Create_Tenant_Request, Create_Tenant_Response, Get_Tenant_Response,
                                                   Is_Tenant_Active)

router = APIRouter()

@router.get("/all-tenants", response_model=list[Get_Tenant_Response])
def get_all_tenants(db: Session = Depends(get_db)):
    try:
        service = TenantService(db)
        result =  service.get_all_tenants()
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/{tenant_id}", response_model=Get_Tenant_Response)
def get_tenant_by_id(tenant_id: int, db: Session = Depends(get_db)):
    try:
        service = TenantService(db)
        return service.get_tenant_by_id(tenant_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/", response_model=Create_Tenant_Response)
def create_tenant(request: Create_Tenant_Request, db: Session = Depends(get_db)):
    try:
        service = TenantService(db)
        result =  service.create_tenant(request)
        return Create_Tenant_Response(
            tenant_id=result,
            message="Tenant created successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/{tenant_id}", response_model=Create_Tenant_Response)
def update_tenant(tenant_id: int, request: Create_Tenant_Request, db: Session = Depends(get_db)):
    try:
        service = TenantService(db)
        service.update_tenant(tenant_id, request)
        return Create_Tenant_Response(
            tenant_id=tenant_id,
            message="Tenant updated successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/deactivate-activate/", response_model=Get_Tenant_Response)
def deactivate_tenant(request: Is_Tenant_Active, db: Session = Depends(get_db)):
    try:
        service = TenantService(db)
        return service.deactivate_tenant(request)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

