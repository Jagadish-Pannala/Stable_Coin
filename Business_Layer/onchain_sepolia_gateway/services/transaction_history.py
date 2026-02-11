import os
import requests
from dotenv import load_dotenv
from utils.redis_client import RedisClient
from DataAccess_Layer.dao.token_dao import TokenDAO


load_dotenv()

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class SepoliaTransactionService:

    def __init__(self, db=None):
        self.token_dao = TokenDAO(db)

        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
        self.alchemy_url = f"https://eth-sepolia.g.alchemy.com/v2/{self.alchemy_api_key}"

        self.redis = RedisClient()

    # ---------------------------------------------------------
    # Classify transaction type
    # ---------------------------------------------------------
    def _classify_tx(self, tx, wallet):

        from_addr = (tx.get("from") or "").lower()
        to_addr = (tx.get("to") or "").lower()
        wallet = wallet.lower()

        if from_addr == ZERO_ADDRESS:
            return "CLAIMED"

        if to_addr == ZERO_ADDRESS:
            return "BURNED"

        if from_addr == wallet:
            return "SENT"

        if to_addr == wallet:
            return "RECEIVED"

        return "UNKNOWN"

    # ---------------------------------------------------------
    # Fetch transfers from Alchemy
    # ---------------------------------------------------------
    def _fetch_alchemy_page(self, wallet, contracts, page_key=None):

        base_params = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "contractAddresses": contracts,
            "category": ["erc20"],
            "withMetadata": True,
            "maxCount": "0x32",
            "pageKey": page_key,
        }

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

        sent_res = requests.post(self.alchemy_url, json=sent_body).json()
        received_res = requests.post(self.alchemy_url, json=received_body).json()

        sent = sent_res.get("result", {})
        received = received_res.get("result", {})

        transfers = [
            *(sent.get("transfers") or []),
            *(received.get("transfers") or []),
        ]

        unique = {tx["hash"]: tx for tx in transfers}.values()

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
    # PUBLIC METHOD WITH REDIS CACHE
    # ---------------------------------------------------------
    def get_transactions(self, tenant_id, wallet_address, offset=0, limit=10):

        wallet_address = wallet_address.lower()

        # ========= STEP 1: CACHE CHECK =========
        cached_all_txs = self.redis.get_full_chain_transactions()

        if cached_all_txs is not None:
            print("✅ Using cached Alchemy transactions")
            return self._filter_transactions_for_address(
                cached_all_txs,
                wallet_address,
                offset,
                limit
            )

        # ========= STEP 2: GET TOKEN CONTRACTS =========
        tokens = self.token_dao.get_tokens_by_tenant(tenant_id)
        contracts = [t.contract_address for t in tokens]

        if not contracts:
            return []

        # ========= STEP 3: FETCH FROM ALCHEMY =========
        all_tx = []
        page_key = None

        while len(all_tx) < offset + limit:

            result = self._fetch_alchemy_page(
                wallet_address,
                contracts,
                page_key
            )

            all_tx.extend(result.get("transfers", []))

            page_key = result.get("pageKey")
            if not page_key:
                break

        # ========= STEP 4: FORMAT =========
        formatted = []

        for tx in all_tx:
            formatted.append({
                "tx_hash": tx.get("hash"),
                "from_address": tx.get("from"),
                "to_address": tx.get("to"),
                "amount": tx.get("value"),
                "asset": tx.get("asset"),
                "timestamp": tx.get("metadata", {}).get("blockTimestamp"),
                "transaction_type": self._classify_tx(tx, wallet_address),
                "status": "SUCCESS",
            })

        # ========= STEP 5: CACHE FULL CHAIN =========
        self.redis.set_full_chain_transactions(formatted, ttl=300)

        # ========= STEP 6: RETURN PAGINATED =========
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
            if tx["from_address"].lower() == address
            or tx["to_address"].lower() == address
        ]

        return filtered[offset:offset + limit]
