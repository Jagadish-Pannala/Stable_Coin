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
            request.mail,
            request.name,
            request.password,
            request.phone_number,
            request.is_active,
            request.fiat_bank_balance
        )
        return CreateUserResponse(
            customer_id=result,
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


