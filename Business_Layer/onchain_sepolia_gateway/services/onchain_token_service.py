import json
from web3 import Web3
from eth_account import Account
from decimal import Decimal


class OnchainTokenService:

    ABI_CACHE = None
    WEB3_CACHE = {}
    CONTRACT_CACHE = {}

    def __init__(self):
        self.rpc_url = None
        self.contract_address = None
        self.private_key = None
        self.web3 = None
        self.contract = None
        self.chain_id = None

    # ---------------- TENANT CONFIG ---------------- #

    def configure(self, rpc_url, contract_address, private_key, chain_id=None):

        self.rpc_url = rpc_url
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.private_key = private_key
        self.chain_id = chain_id

        # -------- Web3 connection caching -------- #
        if rpc_url not in OnchainTokenService.WEB3_CACHE:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                raise Exception("Web3 connection failed")
            OnchainTokenService.WEB3_CACHE[rpc_url] = web3

        self.web3 = OnchainTokenService.WEB3_CACHE[rpc_url]

        # -------- ABI caching -------- #
        if not OnchainTokenService.ABI_CACHE:
            with open(
                r"Business_Layer\onchain_sepolia_gateway\abi\pavescoin_abi.json"
            ) as f:
                OnchainTokenService.ABI_CACHE = json.load(f)

        # -------- Contract caching -------- #
        contract_key = f"{rpc_url}_{contract_address}"

        if contract_key not in OnchainTokenService.CONTRACT_CACHE:
            OnchainTokenService.CONTRACT_CACHE[contract_key] = (
                self.web3.eth.contract(
                    address=self.contract_address,
                    abi=OnchainTokenService.ABI_CACHE
                )
            )

        self.contract = OnchainTokenService.CONTRACT_CACHE[contract_key]

    def _ensure_configured(self):
        if not self.web3 or not self.contract:
            raise Exception("Token service not configured")

    # ---------------- DECIMAL HELPER ---------------- #

    def _to_token_units(self, amount):
        decimals = self.contract.functions.decimals().call()
        return int(Decimal(str(amount)) * (Decimal(10) ** decimals))

    # ---------------- READ METHODS ---------------- #

    def get_balance(self, address):
        self._ensure_configured()
        address = Web3.to_checksum_address(address)
        return self.contract.functions.balanceOf(address).call()
    
    def get_balance_with_decimals(self, address):
        self._ensure_configured()

        address = Web3.to_checksum_address(address)
        raw_balance = self.contract.functions.balanceOf(address).call()
        decimals = self.contract.functions.decimals().call()

        return Decimal(raw_balance) / (Decimal(10) ** decimals)

    # ---------------- GAS OPTIMIZATION ---------------- #

    def _get_fee_params(self):
        try:
            latest_block = self.web3.eth.get_block("latest")

            if "baseFeePerGas" in latest_block:
                base_fee = latest_block["baseFeePerGas"]
                priority_fee = self.web3.eth.max_priority_fee

                return {
                    "maxFeePerGas": int(
                        Decimal(base_fee) * 2 + Decimal(priority_fee)
                    ),
                    "maxPriorityFeePerGas": int(priority_fee),
                }
        except Exception:
            pass

        return {"gasPrice": int(self.web3.eth.gas_price)}

    # ---------------- TX BUILDER ---------------- #

    def _build_and_send_tx(self, function_call):

        self._ensure_configured()

        account = Account.from_key(self.private_key)

        nonce = self.web3.eth.get_transaction_count(
            account.address,
            "pending"
        )

        gas_estimate = function_call.estimate_gas({
            "from": account.address
        })

        fee_params = self._get_fee_params()

        tx = function_call.build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": int(Decimal(gas_estimate) * Decimal("1.2")),
            "chainId": self.chain_id or self.web3.eth.chain_id,
            **fee_params
        })

        signed_tx = self.web3.eth.account.sign_transaction(
            tx,
            self.private_key
        )

        raw_tx = getattr(signed_tx, "raw_transaction", None) \
                 or getattr(signed_tx, "rawTransaction")

        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

        return tx_hash.hex()

    # ---------------- WRITE METHODS ---------------- #

    def transfer(self, to, amount):
        self._ensure_configured()
        to = Web3.to_checksum_address(to)
        amount_units = self._to_token_units(amount)
        return self._build_and_send_tx(
            self.contract.functions.transfer(to, amount_units)
        )

    def mint(self, to, amount):
        self._ensure_configured()
        to = Web3.to_checksum_address(to)
        amount_units = self._to_token_units(amount)
        return self._build_and_send_tx(
            self.contract.functions.mint(to, amount_units)
        )

    def burn(self, from_addr, amount):
        self._ensure_configured()
        from_addr = Web3.to_checksum_address(from_addr)
        amount_units = self._to_token_units(amount)
        return self._build_and_send_tx(
            self.contract.functions.burn(from_addr, amount_units)
        )
