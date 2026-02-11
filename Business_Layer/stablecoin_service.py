from fastapi import HTTPException
from decimal import Decimal

from DataAccess_Layer.dao.token_dao import TokenDAO
from DataAccess_Layer.dao.tenant_dao import TenantDAO
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
from DataAccess_Layer.dao.bank_detail_dao import BankDetailDAO
from DataAccess_Layer.dao.wallet_dao import WalletDAO

from Business_Layer.onchain_sepolia_gateway.services.onchain_token_service import (
    OnchainTokenService
)
from Business_Layer.wallet_service import get_usd_to_inr_rate


class StableCoinService:
    """
    StableCoin Service
    Handles minting and burning using OnchainTokenService
    """

    def __init__(self, db=None):
        self.db = db
        self.token_dao = TokenDAO(db)
        self.tenant_dao = TenantDAO(db)
        self.auth_dao = UserAuthDAO(db)
        self.bank_dao = BankDetailDAO(db)
        self.wallet_dao = WalletDAO(db)

    # ---------------------------------------------------
    # CONFIGURE TOKEN SERVICE
    # ---------------------------------------------------

    def _configure_token_service(self, tenant_id, token_symbol):

        token = self.token_dao.get_token_by_symbol(tenant_id, token_symbol)

        if not token:
            raise HTTPException(404, "Token not found for tenant")

        rpc = self.tenant_dao.get_rpc_by_tenant_id(tenant_id)

        if not rpc:
            raise HTTPException(500, "Tenant RPC config missing")

        service = OnchainTokenService()
        service.configure(
            rpc_url=rpc,
            contract_address=token.contract_address,
            private_key=token.encrypted_private_key,
            chain_id=getattr(token, "chain_id", None)
        )

        return service, token

    # ---------------------------------------------------
    # FIAT BALANCE CHECK (NO UPDATE)
    # ---------------------------------------------------

    def _check_admin_fiat_balance(self, tenant_id, amount, token_symbol):

        if token_symbol.upper() in ["USDC", "USDT"]:
            inr_rate = get_usd_to_inr_rate()
        elif token_symbol.upper() == "ETH":
            inr_rate = Decimal("100")
        else:
            raise HTTPException(400, "Unsupported asset")

        total_inr = Decimal(amount) * Decimal(inr_rate)
        admin_details = self.auth_dao.get_admin_details(tenant_id)

        if admin_details.fiat_bank_balance < total_inr:
            raise HTTPException(400, "Admin has insufficient fiat balance")

        return total_inr, admin_details

    # ---------------------------------------------------
    # UPDATE FIAT BALANCE (AFTER TX SUCCESS)
    # ---------------------------------------------------

    def _update_admin_fiat_balance(self, admin_details, total_inr, minting=True):

        if minting:
            updated_balance = admin_details.fiat_bank_balance - total_inr
        else:
            updated_balance = admin_details.fiat_bank_balance + total_inr

        self.wallet_dao.update_fiat_bank_balance_by_wallet_address(
            admin_details.wallet_address,
            updated_balance
        )

    # ---------------------------------------------------
    # MINT TOKENS
    # ---------------------------------------------------

    def mint_tokens(self, token_symbol, tenant_id, amount):

        # Step 1: Check fiat balance only
        total_inr, admin_details = self._check_admin_fiat_balance(
            tenant_id, amount, token_symbol
        )

        token_service, token = self._configure_token_service(
            tenant_id, token_symbol
        )

        if not token.mint_enabled:
            raise HTTPException(400, "Minting disabled for this token")

        try:
            central_wallet_address = self.auth_dao.get_main_wallet_address(tenant_id)

            tx_hash = token_service.mint(
                central_wallet_address,
                amount
            )

            # Step 2: Update fiat AFTER blockchain success
            self._update_admin_fiat_balance(
                admin_details,
                total_inr,
                minting=True
            )

            return {
                "status": "SUCCESS",
                "operation": "MINT",
                "tx_hash": tx_hash
            }

        except Exception as e:
            raise HTTPException(500, f"Mint failed: {str(e)}")

    # ---------------------------------------------------
    # BURN TOKENS
    # ---------------------------------------------------

    def burn_tokens(self, tenant_id, token_symbol, amount):

        # Optional balance check (depends on business logic)
        total_inr, admin_details = self._check_admin_fiat_balance(
            tenant_id, amount, token_symbol
        )

        token_service, token = self._configure_token_service(
            tenant_id, token_symbol
        )

        if not token.burn_enabled:
            raise HTTPException(400, "Burn disabled for this token")

        try:
            central_wallet_address = self.auth_dao.get_main_wallet_address(tenant_id)

            tx_hash = token_service.burn(
                central_wallet_address,
                amount
            )

            # Update fiat AFTER burn success
            self._update_admin_fiat_balance(
                admin_details,
                total_inr,
                minting=False
            )

            return {
                "status": "SUCCESS",
                "operation": "BURN",
                "tx_hash": tx_hash
            }

        except Exception as e:
            raise HTTPException(500, f"Burn failed: {str(e)}")
