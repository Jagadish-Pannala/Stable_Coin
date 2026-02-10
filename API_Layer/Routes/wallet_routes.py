from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from Business_Layer.wallet_service import WalletService
from ..Interfaces.wallet_interface import (CreateWalletResponse, BalanceResponse, TransferRequest, 
                                           FaucetRequest, FaucetResponse, VerifyAddressResponse , FiatBalanceResponse, BalResponse, SearchResponse,
                                           AssetType)
from sqlalchemy.orm import Session
from DataAccess_Layer.utils.session import get_db 

router = APIRouter()

@router.get("/check-contract")
def checK_contract(address: str):
    try:
        service = WalletService()
        result = service.check_contract(address)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/create", response_model=CreateWalletResponse)
# def create_wallet():
#     service = WalletService()
#     acc = service.create_wallet()
#     return CreateWalletResponse(
#         success=True,
#         address=acc.address,
#         private_key=acc.key.hex(),
#         message="Wallet created"
#     )

@router.get("/balance", response_model=BalResponse)
def balance(tenant_id: str = Query(...),
    wallet_address: str = Query(...), db: Session = Depends(get_db)):
    try:
        service = WalletService(db)
        result = service.check_balance(wallet_address, tenant_id)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/free-tokens")
def create_free_tokens(address: str, type: AssetType, amount: float = 0.0, db: Session = Depends(get_db)):
    try:
        service = WalletService(db)
        result = service.create_free_tokens(FaucetRequest(address=address, type=type, amount=amount))

        return result

    except HTTPException as he:
        # Let FastAPI return proper HTTP status codes
        raise he
    except Exception as e:
        raise HTTPException (status_code=500, detail=str(e))

    except Exception as e:
        return FaucetResponse(
            success=False,
            tx_hash="",
            message=str(e),
            fiat_bank_balance=None
        )




@router.post("/transfer")
def transfer(request: TransferRequest, db: Session = Depends(get_db)):
    try:
        service = WalletService(db)
        result = service.transfer(request)
        return result
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



@router.get("/fiat_balance/{customer_id}")
async def get_fiat_balance_by_customer_id(
    customer_id: str,
    db: Session = Depends(get_db)
):
    service = WalletService(db)

    try:
        return await run_in_threadpool(
            service.get_fiat_balance_by_customer_id,
            customer_id
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-users", response_model=list[SearchResponse])
def search_users(query: str, db: Session = Depends(get_db)):
    service = WalletService(db)
    return service.search_users(query)

@router.get("/search-payees", response_model=list[SearchResponse])
def search_payees(customer_id: str, query: str, db: Session = Depends(get_db)):
    try:
        service = WalletService(db)
        result = service.search_payees(customer_id, query)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))