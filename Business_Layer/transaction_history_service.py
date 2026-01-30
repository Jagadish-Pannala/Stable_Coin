"""
Wallet Service - Handles all wallet and transaction operations with Tenderly
"""

import os
import requests
from typing import Optional, List
from datetime import datetime
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

"""
Wallet Service - Handles all wallet and transaction operations with Tenderly
"""



load_dotenv()


class TransactionService:
    """Service for wallet operations using Tenderly API"""
    
    def __init__(self):
        self.tenderly_account = os.getenv("TENDERLY_ACCOUNT")
        self.tenderly_project = os.getenv("TENDERLY_PROJECT")
        self.tenderly_key = os.getenv("TENDERLY_ACCESS_TOKEN")
        self.network_id = os.getenv("VNET_ID")
        self.faucet_address = os.getenv("FAUCET_ADDRESS", "").lower()
        
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
    
    def transaction_history(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[TransactionHistoryResponse]:
        """
        Fetch transaction history for a given address from Tenderly
        
        Args:
            address: Wallet address to get transactions for (0x...)
            limit: Maximum number of transactions to retrieve (default: 100, max: 100)
            offset: Number of transactions to skip for pagination (default: 0)
            
        Returns:
            List of TransactionHistoryResponse objects sorted by most recent first
            
        Raises:
            HTTPException: If API call fails or address is invalid
        """
        
        # Validate address format
        if not address or not address.startswith("0x") or len(address) != 42:
            logger.warning(f"Invalid address format: {address}")
            raise HTTPException(
                status_code=400,
                detail="Invalid Ethereum address format. Must be 0x followed by 40 hex characters"
            )
        
        # Normalize address to lowercase
        address = address.lower()
        
        try:
            logger.info(f"Fetching transaction history for {address}")
            
            # Build the API URL for Virtual TestNets
            # Virtual TestNets require vnetId in the URL path
            url = f"{self.base_url}/account/{self.tenderly_account}/project/{self.tenderly_project}/vnets/{self.network_id}/transactions"
            
            # Query parameters to filter by address
            params = {
                "address": address,
                "limit": min(limit, 100),  # Cap at 100
                "offset": offset,
                "sort": "blockNumber",
                "order": "desc"  # Most recent first
            }
            
            # DEBUG: Log the URL and credentials
            logger.info(f"Tenderly URL: {url}")
            logger.info(f"Account: {self.tenderly_account}")
            logger.info(f"Project: {self.tenderly_project}")
            logger.info(f"Network ID: {self.network_id}")
            logger.info(f"Access Key: {self.tenderly_key[:10]}...")  # Log first 10 chars only
            
            # Make request to Tenderly API
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            # DEBUG: Log response
            logger.info(f"Tenderly API Response Status: {response.status_code}")
            if response.status_code != 200:
                logger.info(f"Tenderly API Response: {response.text}")
            
            # Check for HTTP errors
            if response.status_code == 401:
                logger.error("Unauthorized: Check your Tenderly API key")
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Invalid Tenderly credentials"
                )
            
            if response.status_code == 404:
                logger.error("Not Found: Check account and project slugs")
                raise HTTPException(
                    status_code=404,
                    detail="Tenderly project or account not found"
                )
            
            if response.status_code != 200:
                error_detail = response.json().get("error", "Unknown error")
                logger.error(f"Tenderly API error ({response.status_code}): {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Tenderly API error: {error_detail}"
                )
            
            # Parse response
            response_data = response.json()
            # Tenderly returns transactions as a list directly
            if isinstance(response_data, list):
                transactions = response_data
            else:
                transactions = response_data.get("transactions", [])
            
            logger.info(f"Retrieved {len(transactions)} transactions for {address}")
            
            # Parse and transform Tenderly transactions to your format
            result = []
            for tx in transactions:
                try:
                    parsed_tx = self._parse_transaction(tx, address)
                    if parsed_tx:  # Only add if successfully parsed
                        result.append(parsed_tx)
                except Exception as e:
                    logger.warning(f"Failed to parse transaction {tx.get('hash')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(result)} transactions")
            return result
            
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except requests.RequestException as e:
            logger.error(f"Network error connecting to Tenderly: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to Tenderly: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching transaction history: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching transaction history: {str(e)}"
            )
    
    def _parse_transaction(
        self,
        tx: dict,
        current_address: str
    ) -> Optional[TransactionHistoryResponse]:
        """
        Parse Tenderly transaction response to your TransactionHistoryResponse format
        
        Args:
            tx: Raw transaction data from Tenderly API
            current_address: The address we're querying for (to determine SENT/RECEIVED)
            
        Returns:
            TransactionHistoryResponse object or None if unable to parse
        """
        
        try:
            current_address = current_address.lower()
            from_address = tx.get("from", "").lower()
            to_address = tx.get("to", "").lower()
            
            # Determine transaction type
            transaction_type = self._determine_transaction_type(
                tx, current_address, from_address, to_address
            )
            
            # Determine status
            status = self._determine_status(tx)
            
            # Get the counterparty address (address2)
            if transaction_type == EnumTransactionType.SENT:
                address2 = to_address
            elif transaction_type == EnumTransactionType.RECEIVED:
                address2 = from_address
            elif transaction_type == EnumTransactionType.CLAIMED:
                address2 = None  # No counterparty for claimed tokens (faucet)
            else:
                address2 = None
            
            # Parse amount and asset
            amount = self._parse_amount(tx)
            asset = self._parse_asset(tx)
            # Skip transactions with zero amount
            if amount == 0:
                return None
            
            # Get timestamp
            timestamp = self._parse_timestamp(tx)
            
            # Get transaction hash - try multiple field names
            tx_hash = tx.get("hash") or tx.get("transaction_hash") or tx.get("tx_hash") or tx.get("transactionHash")
            
            # Build and return response
            return TransactionHistoryResponse(
                address1=current_address,
                address2=address2,
                amount=amount,
                asset=asset,
                status=status,
                tx_hash=tx_hash,
                timestamp=timestamp,
                transaction_type=transaction_type
            )
            
        except Exception as e:
            logger.error(f"Error parsing transaction: {str(e)}")
            return None
    
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
        if self.faucet_address and from_address == self.faucet_address:
            return EnumTransactionType.CLAIMED
        
        # If current address is the sender
        if from_address == current_address:
            return EnumTransactionType.SENT
        
        # If current address is the receiver
        if to_address == current_address:
            return EnumTransactionType.RECEIVED
        
        # Default fallback
        logger.warning(f"Unable to classify transaction type for {tx.get('hash')}")
        return EnumTransactionType.RECEIVED
    
    def _determine_status(self, tx: dict) -> EnumStatus:
        """
        Determine transaction status for Tenderly Virtual TestNet API
        
        Tenderly Virtual TestNets execute transactions synchronously.
        If a transaction is returned from the API, it has been executed successfully.
        
        Status determination:
        - SUCCESS: Transaction executed (default for Tenderly Virtual TestNet)
        - FAILED: If explicitly marked as failed or reverted
        - PENDING: Very rare in Virtual TestNet (would be transactions not yet processed)
        """
        
        # Check if transaction has explicit status field (newer API responses)
        if "status" in tx:
            status = tx.get("status")
            if status == 1 or status == "0x1" or status == "success" or status == "Success":
                return EnumStatus.SUCCESS
            elif status == 0 or status == "0x0" or status == "failed" or status == "Failed":
                return EnumStatus.FAILED
        
        # Check for "reverted" or "error" fields
        if tx.get("reverted") or tx.get("error_message") or tx.get("error"):
            return EnumStatus.FAILED
        
        # Check receipt if available (standard Ethereum response)
        receipt = tx.get("receipt", {})
        if receipt:
            receipt_status = receipt.get("status")
            if receipt_status == 1 or receipt_status == "0x1":
                return EnumStatus.SUCCESS
            elif receipt_status == 0 or receipt_status == "0x0":
                return EnumStatus.FAILED
            
            # If receipt has gasUsed, transaction was processed
            if receipt.get("gasUsed"):
                return EnumStatus.SUCCESS
        
        # For Tenderly Virtual TestNet:
        # Transactions are executed synchronously, so if we receive them from API, they're successful
        # Only mark as PENDING if explicitly indicated or not executed
        if "block_number" in tx and not tx.get("block_number"):
            return EnumStatus.PENDING
        
        # Default: SUCCESS (Tenderly Virtual TestNet processes all transactions)
        return EnumStatus.SUCCESS
        
    def _parse_amount(self, tx: dict) -> float:
        """
        Parse and convert transaction amount from wei to ether
        
        Args:
            tx: Transaction object
            
        Returns:
            Amount in ether as float
        """
        try:
            # Tenderly provides value in wei
            value = tx.get("value", "0")
            
            # Handle hex format (0x...)
            if isinstance(value, str) and value.startswith("0x"):
                amount_wei = int(value, 16)
            else:
                amount_wei = int(value)
            
            # Convert wei to ether (1 ETH = 10^18 wei)
            amount_ether = amount_wei / (10 ** 18)
            
            return round(float(amount_ether), 8)  # 8 decimal places precision
            
        except Exception as e:
            logger.warning(f"Error parsing amount from {tx.get('value')}: {str(e)}")
            return 0.0
    
    def _parse_asset(self, tx: dict) -> str:
        """
        Determine the asset type (ETH for native, token address for ERC20, etc.)
        
        Args:
            tx: Transaction object
            
        Returns:
            Asset identifier (e.g., "ETH", "Token:0x...")
        """
        
        try:
            # Check if there's contract interaction (token transfer)
            input_data = tx.get("input", "0x")
            to_address = tx.get("to", "")
            
            # If input data exists (not just 0x), it's likely a token transfer
            if input_data and input_data != "0x":
                # Return the contract address
                return f"Token:{to_address}"
            
            # Otherwise it's a native ETH transfer
            return "ETH"
            
        except Exception as e:
            logger.warning(f"Error parsing asset: {str(e)}")
            return "ETH"  # Default to ETH
    
    def _parse_timestamp(self, tx: dict) -> Optional[str]:
        """
        Parse timestamp from transaction and convert to ISO format
        
        Tries multiple field names as Tenderly API responses may vary
        """
        try:
            # Try standard timestamp fields
            timestamp = None
            
            # Try different possible field names
            possible_fields = ["timestamp", "block_timestamp", "timeStamp", "time_stamp", "time"]
            
            for field in possible_fields:
                if field in tx and tx[field]:
                    timestamp = tx[field]
                    break
            
            # If no timestamp found, use current time as fallback for successful transactions
            if not timestamp:
                # Virtual TestNet transactions execute immediately, use current time
                return datetime.utcnow().isoformat() + "Z"
            
            # Convert Unix timestamp to datetime then to ISO format
            # Handle both string and integer timestamps
            try:
                timestamp_int = int(timestamp)
                dt = datetime.utcfromtimestamp(timestamp_int)
                return dt.isoformat() + "Z"
            except (ValueError, TypeError):
                # If conversion fails, use current time
                return datetime.utcnow().isoformat() + "Z"
            
        except Exception as e:
            logger.warning(f"Error parsing timestamp: {str(e)}")
            # Return current time as fallback
            return datetime.utcnow().isoformat() + "Z"