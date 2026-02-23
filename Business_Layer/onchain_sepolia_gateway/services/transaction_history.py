import requests
from DataAccess_Layer.dao.token_dao import TokenDAO
from DataAccess_Layer.dao.authentication_dao import UserAuthDAO
from dotenv import load_dotenv
import os


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class SepoliaTransactionService:

    def __init__(self, db=None):
        self.token_dao = TokenDAO(db)
        self.user_dao = UserAuthDAO(db)
        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
        # ------------------------------
        # Temporary Tenant → RPC Mapping
        # ------------------------------
        self.url_map = {
            2: f"https://eth-sepolia.g.alchemy.com/v2/{self.alchemy_api_key}",
            3: f"https://polygon-amoy.g.alchemy.com/v2/{self.alchemy_api_key}",
            # Add more tenants here
        }

    # ---------------------------------------------------------
    # Resolve RPC based on tenant
    # ---------------------------------------------------------
    def _get_rpc_url(self, tenant_id):
        rpc_url = self.url_map.get(tenant_id)
        if not rpc_url:
            raise Exception(f"RPC URL not configured for tenant {tenant_id}")
        return rpc_url

    # ---------------------------------------------------------
    # Classify transaction type
    # ---------------------------------------------------------
    def _classify_tx(self, tx, wallet, main_wallet):

        from_addr = (tx.get("from") or "").lower()
        to_addr = (tx.get("to") or "").lower()
        wallet = wallet.lower()
        main_wallet = (main_wallet or "").lower()

        if from_addr == ZERO_ADDRESS or from_addr == main_wallet:
            return "CLAIMED"

        if to_addr == ZERO_ADDRESS or to_addr == main_wallet:
            return "BURNED"

        if from_addr == wallet:
            return "SENT"

        if to_addr == wallet:
            return "RECEIVED"

        return "UNKNOWN"

    # ---------------------------------------------------------
    # Fetch transfers from Alchemy (dynamic RPC)
    # ---------------------------------------------------------
    def _fetch_alchemy_page(self, rpc_url, wallet, contracts, page_key=None):

        base_params = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "contractAddresses": contracts,
            "category": ["erc20"],
            "withMetadata": True,
            "maxCount": "0x32",
        }

        if page_key:
            base_params["pageKey"] = page_key

        sent_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getAssetTransfers",
            "params": [{**base_params, "fromAddress": wallet}],
        }

        received_body = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "alchemy_getAssetTransfers",
            "params": [{**base_params, "toAddress": wallet}],
        }

        sent_res = requests.post(rpc_url, json=sent_body).json()
        received_res = requests.post(rpc_url, json=received_body).json()

        sent = sent_res.get("result", {})
        received = received_res.get("result", {})

        transfers = [
            *(sent.get("transfers") or []),
            *(received.get("transfers") or []),
        ]

        # Remove duplicate tx hashes
        unique = {tx["hash"]: tx for tx in transfers}.values()

        # Sort newest first
        unique = sorted(
            unique,
            key=lambda x: int(x.get("blockNum", "0x0"), 16),
            reverse=True,
        )

        return {
            "transfers": unique,
            "pageKey": sent.get("pageKey") or received.get("pageKey"),
        }

    # ---------------------------------------------------------
    # PUBLIC METHOD
    # ---------------------------------------------------------
    def get_transactions(self, tenant_id, wallet_address, offset=0, limit=10):

        wallet_address = wallet_address.lower()

        # Resolve RPC dynamically
        rpc_url = self._get_rpc_url(tenant_id)

        main_wallet = self.user_dao.get_main_wallet_address(tenant_id)

        # -------- Get Token Contracts --------
        tokens = self.token_dao.get_tokens_by_tenant(tenant_id)
        contracts = [t.contract_address for t in tokens if t.contract_address]

        if not contracts:
            return []

        # -------- Fetch Transactions --------
        all_tx = []
        page_key = None

        while len(all_tx) < offset + limit:

            result = self._fetch_alchemy_page(
                rpc_url,
                wallet_address,
                contracts,
                page_key
            )

            transfers = result.get("transfers", [])
            if not transfers:
                break

            all_tx.extend(transfers)

            page_key = result.get("pageKey")
            if not page_key:
                break

        # -------- Format Response --------
        formatted = []

        for tx in all_tx:
            formatted.append({
                "tx_hash": tx.get("hash"),
                "from_address": tx.get("from"),
                "to_address": tx.get("to"),
                "amount": tx.get("value"),
                "asset": tx.get("asset"),
                "timestamp": tx.get("metadata", {}).get("blockTimestamp"),
                "transaction_type": self._classify_tx(
                    tx,
                    wallet_address,
                    main_wallet
                ),
                "status": "SUCCESS",
            })

        return self._filter_transactions_for_address(
            formatted,
            wallet_address,
            offset,
            limit
        )

    # ---------------------------------------------------------
    # Filter transactions for specific wallet
    # ---------------------------------------------------------
    def _filter_transactions_for_address(
        self,
        all_transactions,
        address,
        offset,
        limit
    ):
        filtered = [
            tx for tx in all_transactions
            if (tx.get("from_address") or "").lower() == address
            or (tx.get("to_address") or "").lower() == address
        ]

        return filtered[offset:offset + limit]