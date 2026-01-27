import json
from pathlib import Path
from datetime import datetime

class WalletRepository:
    def __init__(self, file_path="wallets.json"):
        self.file_path = Path(file_path)

    def load(self):
        if not self.file_path.exists():
            return []
        return json.loads(self.file_path.read_text())

    def save(self, address, private_key):
        wallets = self.load()
        if not any(w["address"].lower() == address.lower() for w in wallets):
            wallets.append({
                "address": address,
                "private_key": private_key,
                "created_at": datetime.now().isoformat()
            })
            self.file_path.write_text(json.dumps(wallets, indent=2))

    def get_by_address(self, address):
        for wallet in self.load():
            if wallet["address"].lower() == address.lower():
                return wallet
        return None
