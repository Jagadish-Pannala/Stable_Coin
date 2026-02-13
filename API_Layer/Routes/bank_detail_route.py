from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from Business_Layer.bank_detail_service import BankDetailService
from DataAccess_Layer.utils.session import get_db
from sqlalchemy.orm import Session
from API_Layer.Interfaces.bank_detail_interface import (Userdetails, CreateUserRequest, CreateUserResponse, UpdateUserRequest, UpdateAdminRequest,
                                                        CreatePayeeRequest, CreatePayeeResponse, PayeeDetails)
from http import HTTPStatus

router = APIRouter()


@router.get("/customer/{customer_id}", response_model=Userdetails)
async def get_user_details(
    customer_id: str,
    db: Session = Depends(get_db)
):
    try:
        print("customer_id in route:", customer_id)
        service = BankDetailService(db)

        user = await run_in_threadpool(
            service.user_dao.get_user_by_customer_id, customer_id)
        if not user:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="User not found"
            )
        return Userdetails(
            id=user.id,
            name=user.name,
            mail=user.mail,
            tenant_id=user.tenant_id,
            customer_id=user.customer_id,
            phone_number=user.phone_number,
            is_active=user.is_active,
            is_wallet=user.is_wallet,
            wallet_address=user.wallet_address,
            bank_account_number=user.bank_account_number,
            fiat_bank_balance=float(user.fiat_bank_balance) if user.fiat_bank_balance else None,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# update user details by customer_id
@router.put("/customer/{customer_id}", response_model=CreateUserResponse)
async def update_user_details(
    customer_id: str,
    request: UpdateUserRequest,
    db: Session = Depends(get_db)
):
    try:
        service = BankDetailService(db)
        result = service.update_user_details(
            customer_id, request)
        return CreateUserResponse(
            customer_id=customer_id,
            message="User details updated successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.put("/admin/update_user/{customer_id}", response_model=CreateUserResponse)
def admin_update_user_details(
    customer_id: str,
    request: UpdateAdminRequest,
    db: Session = Depends(get_db)):
    try:
        service = BankDetailService(db)
        result = service.admin_update_user_details(
            customer_id, request)
        return CreateUserResponse(
            customer_id=customer_id,
            message="User details updated successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.get("/is_wallet")
def check_wallet_status(customer_id: str, tenant_id: str, db: Session = Depends(get_db)):
    try:
        service = BankDetailService(db)
        user = service.user_dao.get_user_by_customer_id_tenant_id(customer_id, tenant_id)
        if not user:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="User not found"
            )
        return {"is_wallet": user.is_wallet}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
@router.post("/add-balance/{customer_id}")
def add_fiat_balance(
    tenant_id: str,
    customer_id: str,
    amount: float,
    db: Session = Depends(get_db)
):
    try:
        service = BankDetailService(db)
        new_balance = service.add_fiat_balance(tenant_id, customer_id, amount)
        return {
            "customer_id": customer_id,
            "new_fiat_bank_balance": new_balance,
            "message": "Fiat bank balance updated successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.post("/payee/{customer_id}", response_model=CreatePayeeResponse)
def create_payee(
    customer_id: str,
    tenant_id: int,
    request: CreatePayeeRequest,
    db: Session = Depends(get_db)
):
    try:
        service = BankDetailService(db)
        payee_id = service.create_payee(customer_id, tenant_id, request)
        return CreatePayeeResponse(
            payee_id=payee_id,
            message="Payee created successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e))
@router.get("/payees/{customer_id}", response_model=list[PayeeDetails])
def get_payees(customer_id: str, tenant_id: int, db: Session = Depends(get_db)):
    try:
        service = BankDetailService(db)
        payees = service.get_payees(customer_id, tenant_id)
        return payees
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e))
@router.delete("/payee/payee_id", response_model=CreatePayeeResponse)
def delete_payee(customer_id: str, payee_id: int, db: Session = Depends(get_db)):
    try:
        service = BankDetailService(db)
        result = service.delete_payee(customer_id, payee_id)
        if not result:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Payee not found"
            )
        return CreatePayeeResponse(
            payee_id=payee_id,
            message="Payee deleted successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e))