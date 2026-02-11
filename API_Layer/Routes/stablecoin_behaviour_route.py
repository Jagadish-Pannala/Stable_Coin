from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from API_Layer.Interfaces.stablecoin_behaviour_interface import TokenType, TokenActionRequest
from DataAccess_Layer.utils.session import get_db

from Business_Layer.stablecoin_service import StableCoinService
from pydantic import BaseModel, Field
from enum import Enum


router = APIRouter()






# --------------------------------------------------
# Mint Tokens
# --------------------------------------------------
@router.post("/mint")
def mint_tokens(
    token_type: TokenType,
    tenant_id: int = Query(..., example=1),
    tokens: float = Query(..., gt=0, example=10),
    db: Session = Depends(get_db),
):
    try:
        # Block specific tenants
        if tenant_id in [1]:
            raise HTTPException(
                status_code=403,
                detail="Minting not allowed for this tenant"
            )

        service = StableCoinService(db)

        tx_hash = service.mint_tokens(
            token_symbol=token_type,
            tenant_id=tenant_id,
            amount=tokens
        )

        return {
            "status": "success",
            "message": "Tokens minted successfully",
            "tx_hash": tx_hash
        }

    # 👇 Preserve FastAPI HTTPException properly
    except HTTPException:
        raise

    # 👇 Handle unexpected errors only
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/burn")
def burn_tokens(
    token_type: TokenType,
    tenant_id: int = Query(..., example=1),
    tokens: float = Query(..., gt=0, example=10),
    db: Session = Depends(get_db),
):
    try:
        if tenant_id in [1]:
            raise HTTPException(
                status_code=403,
                detail="Burning not allowed for this tenant"
            )

        service = StableCoinService(db)

        tx_hash = service.burn_tokens(
            tenant_id=tenant_id,
            token_symbol=token_type,
            amount=tokens
        )

        return {
            "status": "success",
            "message": "Tokens burned successfully",
            "tx_hash": tx_hash
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
