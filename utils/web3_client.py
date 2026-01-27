import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

class Web3Client:
    def __init__(self):
        rpc_url = os.getenv("PUBLIC_TENDERLY_RPC_URL")
        if not rpc_url:
            raise RuntimeError("PUBLIC_TENDERLY_RPC_URL not set")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError("Failed to connect to Tenderly RPC")
