from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from DataAccess_Layer.models.model import TokenConfig


class TokenDAO:
    def __init__(self, db: Session):
        self.db = db

    # -----------------------------
    # Create new token config
    # -----------------------------
    def create_token(
        self,
        tenant_id: int,
        token_symbol: str,
        contract_address: str,
        central_wallet_address: str,
        encrypted_private_key: str,
        mint_enabled: bool,
        burn_enabled: bool,
        decimals: int,
    ) -> TokenConfig:

        token = TokenConfig(
            tenant_id=tenant_id,
            token_symbol=token_symbol,
            contract_address=contract_address,
            central_wallet_address=central_wallet_address,
            encrypted_private_key=encrypted_private_key,
            mint_enabled=mint_enabled,
            burn_enabled=burn_enabled,
            decimals=decimals,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    # -----------------------------
    # Get token config by symbol + tenant
    # -----------------------------
    def get_token_by_symbol(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> Optional[TokenConfig]:

        return (
            self.db.query(TokenConfig)
            .filter(
                TokenConfig.tenant_id == tenant_id,
                TokenConfig.token_symbol == token_symbol,
                TokenConfig.is_active == True
            )
            .first()
        )

    # -----------------------------
    # Update token config
    # -----------------------------
    def update_token(
        self,
        tenant_id: int,
        token_symbol: str,
        **kwargs
    ) -> Optional[TokenConfig]:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        if not token:
            return None

        for key, value in kwargs.items():
            if hasattr(token, key):
                setattr(token, key, value)

        token.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(token)
        return token

    # -----------------------------
    # Soft delete (Deactivate token)
    # -----------------------------
    def deactivate_token(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> bool:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        if not token:
            return False

        token.is_active = False
        token.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    # -----------------------------
    # Get contract address
    # -----------------------------
    def get_contract_address(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> Optional[str]:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        return token.contract_address if token else None

    # -----------------------------
    # Get central wallet address
    # -----------------------------
    def get_central_wallet(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> Optional[str]:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        return token.central_wallet_address if token else None

    # -----------------------------
    # Get private key (encrypted)
    # -----------------------------
    def get_private_key(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> Optional[str]:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        return token.encrypted_private_key if token else None

    # -----------------------------
    # Check mint enabled
    # -----------------------------
    def is_mint_enabled(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> bool:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        return bool(token and token.mint_enabled)

    # -----------------------------
    # Check burn enabled
    # -----------------------------
    def is_burn_enabled(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> bool:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        return bool(token and token.burn_enabled)

    # -----------------------------
    # Get decimals
    # -----------------------------
    def get_token_decimals(
        self,
        tenant_id: int,
        token_symbol: str
    ) -> Optional[int]:

        token = self.get_token_by_symbol(tenant_id, token_symbol)
        return token.decimals if token else None

    # -----------------------------
    # Get all active tokens for tenant
    # -----------------------------
    def get_tokens_by_tenant(
        self,
        tenant_id: int
    ) -> List[TokenConfig]:

        return (
            self.db.query(TokenConfig)
            .filter(
                TokenConfig.tenant_id == tenant_id,
                TokenConfig.is_active == True
            )
            .all()
        )
