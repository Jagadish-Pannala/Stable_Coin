"""
Transaction History Routes
Endpoints for retrieving wallet transaction history from Tenderly
"""

from fastapi import APIRouter, HTTPException, Path, Query
from typing import List
import logging

# Import your models
from API_Layer.Interfaces.transaction_history_interface import (
    TransactionHistoryResponse)
from Business_Layer.transaction_history_service import TransactionService

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
    )
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
        
        service = TransactionService()
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


@router.get(
    "/transactions/{address}/summary",
    summary="Get transaction summary for a wallet",
    description="Get a summary of transactions (counts and totals) for a specific wallet"
)
def transaction_summary(
    address: str = Path(
        ...,
        description="Ethereum wallet address (format: 0x...)",
        example="0x742d35Cc6634C0532925a3b844Bc955e2e75d30f"
    )
):
    """
    Get a summary of transaction activity for a wallet.
    """
    try:
        if not address or not address.startswith("0x") or len(address) != 42:
            raise HTTPException(
                status_code=400,
                detail="Invalid Ethereum address format"
            )
        
        logger.info(f"Fetching transaction summary for {address}")
        
        service = TransactionService()
        transactions = service.transaction_history(address, limit=100, offset=0)
        
        summary = {
            "address": address,
            "total_transactions": len(transactions),
            "sent": {
                "count": sum(1 for tx in transactions if tx.transaction_type.value == "SENT"),
                "total_amount": sum(
                    tx.amount for tx in transactions
                    if tx.transaction_type.value == "SENT"
                )
            },
            "received": {
                "count": sum(1 for tx in transactions if tx.transaction_type.value == "RECEIVED"),
                "total_amount": sum(
                    tx.amount for tx in transactions
                    if tx.transaction_type.value == "RECEIVED"
                )
            },
            "claimed": {
                "count": sum(1 for tx in transactions if tx.transaction_type.value == "CLAIMED"),
                "total_amount": sum(
                    tx.amount for tx in transactions
                    if tx.transaction_type.value == "CLAIMED"
                )
            },
            "success_count": sum(1 for tx in transactions if tx.status.value == "SUCCESS"),
            "failed_count": sum(1 for tx in transactions if tx.status.value == "FAILED"),
            "pending_count": sum(1 for tx in transactions if tx.status.value == "PENDING")
        }
        
        if summary["total_transactions"] > 0:
            summary["success_rate"] = round(
                (summary["success_count"] / summary["total_transactions"]) * 100,
                2
            )
        else:
            summary["success_rate"] = 0
        
        logger.info(f"Successfully generated summary for {address}")
        return summary
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error generating transaction summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error generating transaction summary"
        )

# @router.get("/daily-transactions/{address}", response_model=List[TransactionHistoryResponse])
# def daily_transactions(address: str, from_date: str = Query(..., description="Start date for transactions (YYYY-MM-DD)"), to_date: str = Query(..., description="End date for transactions (YYYY-MM-DD)")):
#     try:
#         service = TransactionService()
#         result = service.daily_transactions(address, from_date, to_date)
#         return result
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         return{
#             "success": False,
#             "message": str(e)
#         }