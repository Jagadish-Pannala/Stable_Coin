from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from Business_Layer.bank_detail_service import BankDetailService
from DataAccess_Layer.utils.session import get_db
from sqlalchemy.orm import Session
from API_Layer.Interfaces.bank_detail_interface import Userdetails, CreateUserRequest, CreateUserResponse, UpdateUserRequest, UpdateAdminRequest
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
    
@router.get("/is_wallet/{customer_id}")
def check_wallet_status(customer_id: str, db: Session = Depends(get_db)):
    try:
        service = BankDetailService(db)
        user = service.user_dao.get_user_by_customer_id(customer_id)
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