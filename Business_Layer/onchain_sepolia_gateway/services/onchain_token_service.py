import json
from web3 import Web3
from eth_account import Account


class OnchainTokenService:

    ABI_CACHE = None

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

        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.web3.is_connected():
            raise Exception("Web3 connection failed")

        # Load ABI once (cache)
        if not OnchainTokenService.ABI_CACHE:
            with open(
                r"C:\Users\MohanDTeja.Saladi\Desktop\StableCoinDemo\Stable_Coin\Business_Layer\onchain_sepolia_gateway\abi\pavescoin_abi.json"
            ) as f:
                OnchainTokenService.ABI_CACHE = json.load(f)

        self.contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=OnchainTokenService.ABI_CACHE
        )

    def _ensure_configured(self):
        if not self.web3 or not self.contract:
            raise Exception("Token service not configured")

    # ---------------- READ METHODS ---------------- #

    def get_balance(self, address):
        self._ensure_configured()
        address = Web3.to_checksum_address(address)
        return self.contract.functions.balanceOf(address).call()

    def total_supply(self):
        self._ensure_configured()
        return self.contract.functions.totalSupply().call()

    # ---------------- GAS OPTIMIZATION ---------------- #

    def _get_fee_params(self):
        """
        Use EIP-1559 gas if supported,
        fallback to legacy gas price.
        """

        try:
            latest_block = self.web3.eth.get_block("latest")

            if "baseFeePerGas" in latest_block:
                base_fee = latest_block["baseFeePerGas"]
                priority_fee = self.web3.eth.max_priority_fee

                return {
                    "maxFeePerGas": int(base_fee * 2 + priority_fee),
                    "maxPriorityFeePerGas": int(priority_fee),
                }

        except Exception:
            pass

        return {"gasPrice": self.web3.eth.gas_price}

    # ---------------- TX BUILDER ---------------- #

    def _build_and_send_tx(self, function_call):

        self._ensure_configured()

        account = Account.from_key(self.private_key)

        nonce = self.web3.eth.get_transaction_count(
            account.address,
            "pending"
        )

        # Estimate gas dynamically
        gas_estimate = function_call.estimate_gas({
            "from": account.address
        })

        fee_params = self._get_fee_params()

        tx = function_call.build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": int(gas_estimate * 1.2),
            "chainId": self.chain_id or self.web3.eth.chain_id,
            **fee_params
        })

        signed_tx = self.web3.eth.account.sign_transaction(
            tx,
            self.private_key
        )

        # Compatible with Web3 v5 & v6
        raw_tx = getattr(signed_tx, "raw_transaction", None) \
                 or getattr(signed_tx, "rawTransaction")

        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

        return tx_hash.hex()

    # ---------------- WRITE METHODS ---------------- #

    def transfer(self, to, amount):
        self._ensure_configured()
        to = Web3.to_checksum_address(to)

        return self._build_and_send_tx(
            self.contract.functions.transfer(to, int(amount))
        )

    def approve(self, spender, amount):
        self._ensure_configured()
        spender = Web3.to_checksum_address(spender)

        return self._build_and_send_tx(
            self.contract.functions.approve(spender, int(amount))
        )

    def transfer_from(self, sender, recipient, amount):
        self._ensure_configured()

        sender = Web3.to_checksum_address(sender)
        recipient = Web3.to_checksum_address(recipient)

        return self._build_and_send_tx(
            self.contract.functions.transferFrom(
                sender,
                recipient,
                int(amount)
            )
        )

    def mint(self, to, amount):
        self._ensure_configured()
        to = Web3.to_checksum_address(to)

        return self._build_and_send_tx(
            self.contract.functions.mint(to, int(amount))
        )

    def burn(self, from_addr, amount):
        self._ensure_configured()
        from_addr = Web3.to_checksum_address(from_addr)

        return self._build_and_send_tx(
            self.contract.functions.burn(from_addr, int(amount))
        )
