from fastapi import APIRouter, Depends
from Business_Layer.wallet_service import WalletService
from ..Interfaces.wallet_interface import CreateWalletResponse, BalanceResponse, TransferRequest, FaucetRequest, FaucetResponse
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
def transfer(req: TransferRequest):
    return service.transfer(req)
