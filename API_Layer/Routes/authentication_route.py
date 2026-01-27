from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..Interfaces.authentication import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    UpdatePasswordRequest,
    UpdatePasswordResponse,
)

from Business_Layer.authentication_service import AuthenticationService
from DataAccess_Layer.utils.session import get_db 

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register_user(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    service = AuthenticationService(db)

    try:
        new_user = await run_in_threadpool(
            service.register_user,
            request.email,
            request.name,
            request.password
        )

        return RegisterResponse(
            success=True,
            userid=new_user.user_id,
            message="User registered successfully"
        )

    except ValueError as ve:
        return RegisterResponse(
            success=False,
            message=str(ve)
        )


@router.post("/login", response_model=LoginResponse)
async def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    service = AuthenticationService(db)

    user = await run_in_threadpool(
        service.authenticate_user,
        request.username,
        request.password
    )

    if not user:
        return LoginResponse(
            success=False,
            message="Invalid username or password"
        )

    return LoginResponse(
        success=True,
        userid=user.user_id,
        message="Login successful"
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


@router.get("/{user_id}")
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db)
):
    service = AuthenticationService(db)

    user = await run_in_threadpool(
        service.user_dao.get_user_by_id,
        user_id
    )

    if not user:
        return {"success": False, "message": "User not found"}

    return {
        "success": True,
        "user_id": user.user_id,
        "email": user.mail,
        "name": user.name,
        "wallet_address": user.wallet_address,
        "is_active": user.is_active
    }
