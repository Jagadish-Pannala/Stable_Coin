from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from http import HTTPStatus

from ..Interfaces.authentication import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    Userdetails,
    UpdatePasswordRequest,
    UpdatePasswordResponse,
)

from Business_Layer.authentication_service import AuthenticationService
from DataAccess_Layer.utils.session import get_db 

router = APIRouter()


# @router.post("/register", response_model=RegisterResponse)
# async def register_user(
#     request: RegisterRequest,
#     db: Session = Depends(get_db)
# ):
#     service = AuthenticationService(db)

#     try:
#         new_user = await run_in_threadpool(
#             service.register_user,
#             request.email,
#             request.name,
#             request.password
#         )

#         return RegisterResponse(
#             success=True,
#             userid=new_user.user_id,
#             message="User registered successfully"
#         )

#     except ValueError as ve:
#         raise HTTPException(
#                     status_code=401,
#                     detail=str(ve)
#                 )


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


@router.post("/update-password", response_model=UpdatePasswordResponse)
async def update_password(
    request: UpdatePasswordRequest,
    db: Session = Depends(get_db)
):
    service = AuthenticationService(db)

    try:
        await run_in_threadpool(
            service.update_password_by_mail,
            request.email,
            request.new_password
        )

        return UpdatePasswordResponse(
            success=True,
            message="Password updated successfully"
        )

    except ValueError as ve:
        return UpdatePasswordResponse(
            success=False,
            message=str(ve)
        )


@router.get("/{user_id}", response_model=Userdetails)
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db)
):
    try:
        service = AuthenticationService(db)

        user = await run_in_threadpool(
            service.user_dao.get_user_by_id,
            user_id
        )
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

    
    