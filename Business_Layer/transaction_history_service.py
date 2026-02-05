"""
Wallet Service - Handles all wallet and transaction operations with Tenderly
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
    
    def transaction_history(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0
    ):
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
            # logger.warning(f"Invalid address format: {address}")
            raise HTTPException(
                status_code=400,
                detail="Invalid Ethereum address format. Must be 0x followed by 40 hex characters"
            )
        
        # Normalize address to lowercase
        address = address.lower()
        # logger.info(f"Fetching transaction history for {address}")
        
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
        # logger.info(f"Tenderly URL: {url}")
        # logger.info(f"Account: {self.tenderly_account}")
        # logger.info(f"Project: {self.tenderly_project}")
        # logger.info(f"Network ID: {self.network_id}")
        # logger.info(f"Access Key: {self.tenderly_key[:10]}...")  # Log first 10 chars only
        
        # Make request to Tenderly API
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )
        
        # DEBUG: Log response
        # logger.info(f"Tenderly API Response Status: {response.status_code}")
        if response.status_code != 200:
            logger.info(f"Tenderly API Response: {response.text}")
        
        # Check for HTTP errors
        if response.status_code == 401:
            # logger.error("Unauthorized: Check your Tenderly API key")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid Tenderly credentials"
            )
        
        if response.status_code == 404:
            # logger.error("Not Found: Check account and project slugs")
            raise HTTPException(
                status_code=404,
                detail="Tenderly project or account not found"
            )
        
        if response.status_code != 200:
            error_detail = response.json().get("error", "Unknown error")
            # logger.error(f"Tenderly API error ({response.status_code}): {error_detail}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Tenderly API error: {error_detail}"
            )
        
        # Parse response
        response_data = response.json()
        # print("response_data:", response_data)
        # Tenderly returns transactions as a list directly
        if isinstance(response_data, list):
            transactions = response_data
        else:
            transactions = response_data.get("transactions", [])
        
        # logger.info(f"Retrieved {len(transactions)} transactions")
        result = []
        # print("transactions:", transactions[:2])
        for tx in transactions:
            my_dict = {}
            from_address = tx.get("from", "").lower()
            asset = self.parse_asset(tx)
            if asset == "USDC":
                to_address = self.parse_to_address(tx)
            else:
                to_address = tx.get("to", "").lower()
            print("from_address:", from_address)
            print("to_address:", to_address)
            if from_address == address.lower() or to_address == address.lower():
                if tx.get('rpc_method') == "eth_sendRawTransaction" and asset == "ETH":
                    my_dict['from_address'] = from_address
                    my_dict['to_address'] = to_address
                    my_dict['amount'] = self.parse_amount(tx)
                    my_dict['asset'] = self.parse_asset(tx)
                    my_dict['status'] = self.parse_status(tx)
                    my_dict['tx_hash'] = tx.get("tx_hash", "")
                    my_dict['timestamp'] = self.utc_iso_to_local_str(tx.get("created_at", ""))
                    my_dict['transaction_type'] = self._determine_transaction_type(
                        tx, address, from_address, to_address)
                    result.append(my_dict)
                elif tx.get('rpc_method') == "eth_sendRawTransaction" and asset == "USDC":
                    my_dict['from_address'] = from_address
                    my_dict["to_address"] = to_address
                    my_dict['amount'] = self.parse_usdc_amount(tx)
                    my_dict['asset'] = self.parse_asset(tx)
                    my_dict['status'] = self.parse_status(tx)
                    my_dict['tx_hash'] = tx.get("tx_hash", "")
                    my_dict['timestamp'] = self.utc_iso_to_local_str(tx.get("created_at", ""))
                    my_dict['transaction_type'] = self._determine_transaction_type(
                        tx, address, from_address, to_address)
                    result.append(my_dict)

        # print("result:", result)
        return result
    def daily_transactions(self, address: str, from_date: str, to_date: str):
        # Validate address format
        if not address or not address.startswith("0x") or len(address) != 42:
            # logger.warning(f"Invalid address format: {address}")
            raise HTTPException(
                status_code=400,
                detail="Invalid Ethereum address format. Must be 0x followed by 40 hex characters"
            )
        
        # Normalize address to lowercase
        address = address.lower()
        
        # Build the API URL for Virtual TestNets
        # Virtual TestNets require vnetId in the URL path
        url = f"{self.base_url}/account/{self.tenderly_account}/project/{self.tenderly_project}/vnets/{self.network_id}/transactions"
        
        # Query parameters to filter by address
        params = {
            "address": address,
            "from_date": from_date,
            "to_date": to_date,
            "sort": "blockNumber",
            "order": "desc"  # Most recent first
        }
        
        
        # Make request to Tenderly API
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )
        
        # DEBUG: Log response
        # logger.info(f"Tenderly API Response Status: {response.status_code}")
        if response.status_code != 200:
            logger.info(f"Tenderly API Response: {response.text}")
        
        # Check for HTTP errors
        if response.status_code == 401:
            # logger.error("Unauthorized: Check your Tenderly API key")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid Tenderly credentials"
            )
        
        if response.status_code == 404:
            # logger.error("Not Found: Check account and project slugs")
            raise HTTPException(
                status_code=404,
                detail="Tenderly project or account not found"
            )
        
        if response.status_code != 200:
            error_detail = response.json().get("error", "Unknown error")
            # logger.error(f"Tenderly API error ({response.status_code}): {error_detail}")
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
        result = []
        # print("transactions:", transactions[:2])
        for tx in transactions:
            my_dict = {}
            from_address = tx.get("from", "").lower()
            asset = self.parse_asset(tx)
            if asset == "USDC":
                to_address = self.parse_to_address(tx)
            else:
                to_address = tx.get("to", "").lower()
            if from_address == address.lower() or to_address == address.lower():
                if tx.get('rpc_method') == "eth_sendRawTransaction" and asset == "ETH":
                    my_dict['from_address'] = from_address
                    my_dict['to_address'] = to_address
                    my_dict['amount'] = self.parse_amount(tx)
                    my_dict['asset'] = self.parse_asset(tx)
                    my_dict['status'] = self.parse_status(tx)
                    my_dict['tx_hash'] = tx.get("tx_hash", "")
                    my_dict['timestamp'] = self.utc_iso_to_local_str(tx.get("created_at", ""))
                    my_dict['transaction_type'] = self._determine_transaction_type(
                        tx, address, from_address, to_address)
                    result.append(my_dict)
                elif tx.get('rpc_method') == "eth_sendRawTransaction" and asset == "USDC":
                    my_dict['from_address'] = from_address
                    my_dict["to_address"] = to_address
                    my_dict['amount'] = self.parse_usdc_amount(tx)
                    my_dict['asset'] = self.parse_asset(tx)
                    my_dict['status'] = self.parse_status(tx)
                    my_dict['tx_hash'] = tx.get("tx_hash", "")
                    my_dict['timestamp'] = self.utc_iso_to_local_str(tx.get("created_at", ""))
                    my_dict['transaction_type'] = self._determine_transaction_type(
                        tx, address, from_address, to_address)
                    result.append(my_dict)

        # print("result:", result)
        return result



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
        if ip and ip!='0x':
            return f"USDC"
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
        # print("from_address:", from_address)
        # print("to_address:", to_address)
        # print("current_address:", current_address)
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
        # # logger.warning(f"Unable to classify transaction type for {tx.get('hash')}")
        return EnumTransactionType.RECEIVED
            
            