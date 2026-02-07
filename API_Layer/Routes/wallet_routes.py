from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from Business_Layer.wallet_service import WalletService
from ..Interfaces.wallet_interface import (CreateWalletResponse, BalanceResponse, TransferRequest, 
                                           FaucetRequest, FaucetResponse, VerifyAddressResponse , FiatBalanceResponse, BalResponse, SearchResponse,
                                           AssetType)
from sqlalchemy.orm import Session
from DataAccess_Layer.utils.session import get_db 

router = APIRouter()

@router.get("/check-contract")
def checK_contract():
    try:
        service = WalletService()
        service.check_contract()
        return {"message": "Contract check successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=CreateWalletResponse)
def create_wallet():
    service = WalletService()
    acc = service.create_wallet()
    return CreateWalletResponse(
        success=True,
        address=acc.address,
        private_key=acc.key.hex(),
        message="Wallet created"
    )
# @router.get("/list-wallets")
# def list_wallets(db: Session = Depends(get_db)):
#     try:
#         service = WalletService(db)
#         result = service.list_wallets()
#         return result
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         return {
#             "success": False,
#             "message": str(e)
#         }

@router.get("/balance/{address}", response_model=BalanceResponse)
def balance(address: str):
    try:
        service = WalletService()
        result = service.check_balance(address)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/free-tokens", response_model=FaucetResponse)
def create_free_tokens(address: str, type: AssetType, amount: float = 0.0, db: Session = Depends(get_db)):
    try:
        service = WalletService(db)
        result = service.create_free_tokens(FaucetRequest(address=address, type=type, amount=amount))

        return FaucetResponse(
            success=True,
            tx_hash=result["tx_hash"],
            message="Faucet successful",
            fiat_bank_balance=result.get("fiat_bank_balance", 0.0)
        )

    except HTTPException:
        # Let FastAPI return proper HTTP status codes
        raise

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
        return {
            "success": True,
            "tx_hash": result["tx_hash"],
            "message": "Transfer successful",
            "fiat_bank_balance": result.get("fiat_bank_balance")
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

# # Transaction history
# @router.get("/transactions/{address}", response_model=list[TransactionHistoryResponse])
# def transaction_history(address: str):
#     try:
#         service = WalletService()
#         result = service.transaction_history(address)
#         return result
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         return{
#             "success": False,
#             "message": str(e)
#         }

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

@router.get("/bal/{address}", response_model=BalResponse)
def get_balance(address: str, db: Session = Depends(get_db)):
    service = WalletService(db)
    return service.get_balance(address)

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