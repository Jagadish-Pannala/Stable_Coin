from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from http import HTTPStatus

from ..Interfaces.authentication import (
    LoginRequest,
    LoginResponse,
    Userdetails,
    CreateUserRequest,
    CreateUserResponse,
    CreateWalletResponse,
    UpdateUserRequest,
    UpdateAdminRequest
)

from Business_Layer.authentication_service import AuthenticationService
from DataAccess_Layer.utils.session import get_db 

router = APIRouter()


# creating user without wallet
@router.post("/create_user_without_wallet", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
):
    try:
        service = AuthenticationService(db)
        result = await run_in_threadpool(
            service.create_user,
            request.tenant_id,
            request.customer_id,
            request.mail,
            request.name,
            request.password,
            request.phone_number,
            request.bank_account_number,
            request.is_active,
            request.fiat_bank_balance
        )
        return CreateUserResponse(
            customer_id=request.customer_id,
            message="User created successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# creating  wallets for existing users
@router.post("/create_wallet/{customer_id}", response_model=CreateWalletResponse)
async def create_wallet_for_user(
    customer_id: str,
    db: Session = Depends(get_db)
):
    try:
        service = AuthenticationService(db)
        result = await run_in_threadpool(
            service.create_wallet_for_user,
            customer_id
        )
        return CreateWalletResponse(
            wallet_address=result,
            message="Wallet created successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.post("/login", response_model=LoginResponse)
async def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    try:
        service = AuthenticationService(db)
        result = await run_in_threadpool(
            service.authenticate_user,
            request.mail,
            request.password)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )




@router.get("/customer/{customer_id}", response_model=Userdetails)
async def get_user_details(
    customer_id: str,
    db: Session = Depends(get_db)
):
    try:
        print("customer_id in route:", customer_id)
        service = AuthenticationService(db)

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
        service = AuthenticationService(db)
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
        service = AuthenticationService(db)
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
    