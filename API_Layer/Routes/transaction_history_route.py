"""
Transaction History Routes
Endpoints for retrieving wallet transaction history from Tenderly
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List
import logging

# Import your models
from API_Layer.Interfaces.transaction_history_interface import (
    TransactionHistoryResponse)
from Business_Layer.transaction_history_service import TransactionService
from DataAccess_Layer.utils.session import get_db 
from sqlalchemy.orm import Session

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/transactions/{address}", response_model=List[TransactionHistoryResponse])
def transaction_history(
    address: str = Path(
        ...,
        description="Ethereum wallet address (format: 0x...)",
        example="0x742d35Cc6634C0532925a3b844Bc955e2e75d30f"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of transactions to return (1-100)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of transactions to skip for pagination"
    ),
    db: Session = Depends(get_db)
):
    """
    Get transaction history for a specific wallet address.
    """
    try:
        if not address or not address.startswith("0x") or len(address) != 42:
            raise HTTPException(
                status_code=400,
                detail="Invalid Ethereum address format. Must be 0x followed by 40 hex characters"
            )
        
        logger.info(f"Fetching transaction history for {address}")
        
        service = TransactionService(db)
        result = service.transaction_history(address, limit=limit, offset=offset)
        
        logger.info(f"Successfully retrieved {len(result)} transactions for {address}")
        return result
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in transaction_history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching transaction history"
        )

