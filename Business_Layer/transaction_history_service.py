"""
Wallet Service - Handles all wallet and transaction operations with Tenderly
NOW WITH REDIS CACHING
"""

import os
import requests
from typing import Optional, List
from datetime import datetime, timezone
from dateutil.parser import isoparse
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from fastapi import HTTPException
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your models
from API_Layer.Interfaces.transaction_history_interface import (
    TransactionHistoryResponse,
    EnumStatus,
    EnumTransactionType
)

from DataAccess_Layer.dao.wallet_dao import WalletDAO
# Import Redis client
from utils.redis_client import RedisClient

from DataAccess_Layer.utils.session import get_db 


load_dotenv()


class TransactionService:
    """Service for wallet operations using Tenderly API with Redis caching"""
    
    def __init__(self, db=None):
        self.db = db
        self.wallet_dao = WalletDAO(db)
        self.tenderly_account = os.getenv("TENDERLY_ACCOUNT")
        self.tenderly_project = os.getenv("TENDERLY_PROJECT")
        self.tenderly_key = os.getenv("TENDERLY_ACCESS_TOKEN")
        self.network_id = os.getenv("VNET_ID")
        self.faucet_address = os.getenv("MAIN_WALLET_ADDRESS", "").lower()
        
        # Validate required config
        if not all([self.tenderly_account, self.tenderly_project, self.tenderly_key]):
            raise ValueError("Missing Tenderly configuration in environment variables")
        
        # Base URL for Tenderly API
        self.base_url = "https://api.tenderly.co/api/v1"
        
        # Headers for authentication
        self.headers = {
            "X-Access-Key": self.tenderly_key,
            "Content-Type": "application/json"
        }
        
        # Initialize Redis client
        self.redis = RedisClient()
    
    def transaction_history(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0
    ):
        """
        Fetch transaction history for a given address
        
        CACHING STRATEGY:
        1. Try to get full chain transactions from Redis cache
        2. If cache hit: Filter for this address and return
        3. If cache miss: Fetch from Tenderly, cache, filter, return
        
        Args:
            address: Wallet address to get transactions for (0x...)
            limit: Maximum number of transactions to retrieve (default: 100, max: 100)
            offset: Number of transactions to skip for pagination (default: 0)
            
        Returns:
            List of TransactionHistoryResponse objects sorted by most recent first
            
        Raises:
            HTTPException: If API call fails or address is invalid
        """
        
        tenant_id = self.wallet_dao.get_tenant_id_by_address(address)
        print(tenant_id)
        # Validate address format
        if not address or not address.startswith("0x") or len(address) != 42:
            raise HTTPException(
                status_code=400,
                detail="Invalid Ethereum address format. Must be 0x followed by 40 hex characters"
            )
        
        # Normalize address to lowercase
        address = address.lower()
        logger.info(f"📋 Fetching transaction history for {address}")

        if tenant_id == 1:
        
            # ========== STEP 1: TRY CACHE ==========
            
            cached_all_txs = self.redis.get_full_chain_transactions()
            
            if cached_all_txs is not None:
                logger.info("✅ Using cached chain transactions")
                # Filter for this user and return
                return self._filter_transactions_for_address(cached_all_txs, address)
            
            # ========== STEP 2: CACHE MISS - FETCH FROM TENDERLY ==========
            
            logger.info("❌ Cache miss - Fetching from Tenderly")
            
            # Build the API URL for Virtual TestNets
            url = f"{self.base_url}/account/{self.tenderly_account}/project/{self.tenderly_project}/vnets/{self.network_id}/transactions"
            
            # Query parameters (address is ignored by Tenderly, but we keep it for clarity)
            params = {
                "address": address,  # Ignored by Tenderly
                "limit": min(limit, 100),
                "offset": offset,
                "sort": "blockNumber",
                "order": "desc"
            }
            
            # Make request to Tenderly API
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            # Check for HTTP errors
            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Invalid Tenderly credentials"
                )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Tenderly project or account not found"
                )
            
            if response.status_code != 200:
                error_detail = response.json().get("error", "Unknown error")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Tenderly API error: {error_detail}"
                )
            
            # Parse response
            response_data = response.json()
            
            if isinstance(response_data, list):
                all_transactions = response_data
            else:
                all_transactions = response_data.get("transactions", [])
            
            logger.info(f"📦 Retrieved {len(all_transactions)} total chain transactions from Tenderly")
            
            # ========== STEP 3: CACHE THE FULL CHAIN DATA ==========
            
            self.redis.set_full_chain_transactions(all_transactions, ttl=300)  # 5 min cache
            
            # ========== STEP 4: FILTER FOR THIS USER ==========
            
            return self._filter_transactions_for_address(all_transactions, address)
        
        else:
            from .onchain_sepolia_gateway.services.transaction_history import SepoliaTransactionService

            sepolia_service = SepoliaTransactionService(self.db)
            return sepolia_service.get_transactions(tenant_id, address, offset=offset, limit=limit)
        
    
    def _filter_transactions_for_address(self, all_transactions: list, address: str) -> list:
        """
        Filter full chain transactions for a specific address
        
        Args:
            all_transactions: All chain transactions from Tenderly
            address: Address to filter for (lowercase)
            
        Returns:
            List of transactions relevant to this address
        """
        result = []
        
        for tx in all_transactions:
            my_dict = {}
            from_address = tx.get("from", "").lower()
            asset = self.parse_asset(tx)
            
            if asset == "USDC" or asset == "USDT":
                to_address = self.parse_to_address(tx)
            else:
                to_address = tx.get("to", "").lower()
            
            # Only include if this address is involved
            if from_address == address or to_address == address:
                
                if tx.get('rpc_method') == "eth_sendRawTransaction" and asset == "ETH":
                    my_dict['from_address'] = from_address
                    my_dict['to_address'] = to_address
                    my_dict['amount'] = self.parse_amount(tx)
                    my_dict['asset'] = asset
                    my_dict['status'] = self.parse_status(tx)
                    my_dict['tx_hash'] = tx.get("tx_hash", "")
                    my_dict['timestamp'] = self.utc_iso_to_local_str(tx.get("created_at", ""))
                    my_dict['transaction_type'] = self._determine_transaction_type(
                        tx, address, from_address, to_address
                    )
                    result.append(my_dict)
                
                elif tx.get('rpc_method') == "eth_sendRawTransaction" and (asset == "USDC" or asset == "USDT"):
                    my_dict['from_address'] = from_address
                    my_dict["to_address"] = to_address
                    my_dict['amount'] = self.parse_usdc_amount(tx)
                    my_dict['asset'] = asset
                    my_dict['status'] = self.parse_status(tx)
                    my_dict['tx_hash'] = tx.get("tx_hash", "")
                    my_dict['timestamp'] = self.utc_iso_to_local_str(tx.get("created_at", ""))
                    my_dict['transaction_type'] = self._determine_transaction_type(
                        tx, address, from_address, to_address
                    )
                    result.append(my_dict)
        
        logger.info(f"🔍 Filtered to {len(result)} transactions for {address}")
        return result
    
    # ========== CACHE INVALIDATION METHOD ==========
    
    def invalidate_transaction_cache(self):
        """
        Invalidate the full chain transaction cache
        
        CALL THIS AFTER:
        - /free-tokens (faucet claim)
        - /transfer (user-to-user transfer)
        
        This forces the next history request to fetch fresh data from Tenderly
        """
        logger.info("🗑️  Invalidating transaction cache...")
        self.redis.invalidate_full_chain_cache()
    
    # ========== PARSING HELPERS (UNCHANGED) ==========
    
    def parse_to_address(self, tx):
        input_data = tx.get("input", "")
        if input_data and len(input_data) >= 74:
            to_address = "0x" + input_data[34:74]
            return to_address.lower()
        return ""
    
    def parse_usdc_amount(self, tx):
        input_data = tx.get("input", "")
        if input_data and len(input_data) >= 138:
            amount_hex = input_data[74:138]
            amount_wei = int(amount_hex, 16)
            # USDC has 6 decimal places
            amount_usdc = amount_wei / (10 ** 6)
            return round(float(amount_usdc), 8)
        return 0.0

    def parse_asset(self, tx):
        ip = tx.get("input", "")
        to = tx.get("to", "")
        if ip and ip != '0x' and to == '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48':
            return "USDC"
        elif ip and ip != '0x' and to == '0xdac17f958d2ee523a2206206994597c13d831ec7':
            return "USDT"
        return "ETH"
    
    def parse_amount(self, tx):
        value = tx.get("value", "0")
        if isinstance(value, str) and value.startswith("0x"):
            amount_wei = int(value, 16)
        else:
            amount_wei = int(value)
        
        # Convert wei to ether (1 ETH = 10^18 wei)
        amount_ether = amount_wei / (10 ** 18)
        
        return round(float(amount_ether), 8)
    
    def parse_status(self, tx):
        status = tx.get("status", "").lower()
        if status == "success":
            return EnumStatus.SUCCESS
        elif status == "failed":
            return EnumStatus.FAILED
        else:
            return EnumStatus.PENDING
    
    def utc_iso_to_local_str(self, iso_utc: str) -> str:
        if not iso_utc:
            return ""

        dt_utc = isoparse(iso_utc)

        # Ensure UTC timezone
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)

        dt_local = dt_utc.astimezone()
        return dt_local.strftime("%d-%m-%Y %H:%M:%S")
    
    def _determine_transaction_type(
        self,
        tx: dict,
        current_address: str,
        from_address: str,
        to_address: str
    ) -> EnumTransactionType:
        """
        Determine if transaction is SENT, RECEIVED, or CLAIMED
       
        Logic:
        - CLAIMED: from faucet address to current user
        - SENT: from current user to another address
        - RECEIVED: from another address to current user
        """
        # Check if this is a faucet transaction (CLAIMED)
        if from_address == self.faucet_address and to_address == current_address:
            return EnumTransactionType.CLAIMED
        
        # check if received to faucet address (BURNED)
        if to_address == self.faucet_address and from_address == current_address:
            return EnumTransactionType.BURNED
        
        # If current address is the sender
        if from_address == current_address:
            return EnumTransactionType.SENT
       
        # If current address is the receiver
        if to_address == current_address:
            return EnumTransactionType.RECEIVED
       
        # Default fallback
        return EnumTransactionType.RECEIVED