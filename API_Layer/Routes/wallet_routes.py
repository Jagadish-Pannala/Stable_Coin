from fastapi import APIRouter, Depends, HTTPException
from Business_Layer.wallet_service import WalletService
from ..Interfaces.wallet_interface import (CreateWalletResponse, BalanceResponse, TransferRequest, 
                                           FaucetRequest, FaucetResponse, VerifyAddressResponse)
from sqlalchemy.orm import Session
from DataAccess_Layer.utils.session import get_db 

router = APIRouter()
service = WalletService()

@router.post("/create", response_model=CreateWalletResponse)
def create_wallet():
    acc = service.create_wallet()
    return CreateWalletResponse(
        success=True,
        address=acc.address,
        private_key=acc.key.hex(),
        message="Wallet created"
    )
@router.get("/list-wallets")
def list_wallets(db: Session = Depends(get_db)):
    return service.list_wallets(db)

@router.get("/balance/{address}", response_model=BalanceResponse)
def balance(address: str):
    return service.check_balance(address)

@router.post("/free-tokens/{address}", response_model=FaucetResponse)
def create_free_tokens(request: FaucetRequest):
    try:
        result= service.create_free_tokens(request)
        return FaucetResponse(
            success=True,
            tx_hash=result["tx_hash"],
            message="Faucet successful"
        )
    except Exception as e:
        return str(e)



@router.post("/transfer")
def transfer(request: TransferRequest, db: Session = Depends(get_db)):
    try:
        service = WalletService(db)
        result = service.transfer(request)
        return {
            "success": True,
            "tx_hash": result["tx_hash"],
            "message": "Transfer successful"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
    
@router.post("/verify-address/{address}", response_model=VerifyAddressResponse)
def verify_address(address: str):
    try:
        service = WalletService()
        result = service.verify_address(address)
        return VerifyAddressResponse(
            address=address,
            is_valid=result
        
    )
    except HTTPException as he:
        raise he
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

