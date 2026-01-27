from fastapi import APIRouter
from Business_Layer.wallet_service import WalletService
from ..Interfaces.wallet_interface import CreateWalletResponse, BalanceResponse, TransferRequest

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
def list_wallets():
    return service.list_wallets()

@router.get("/balance/{address}", response_model=BalanceResponse)
def balance(address: str):
    return service.check_balance(address)

@router.post("/transfer")
def transfer(req: TransferRequest):
    return service.transfer(req)
