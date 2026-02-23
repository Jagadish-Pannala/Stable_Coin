from eth_account import Account
import json

def encrypt_existing_private_key(private_key: str, password: str):
    try:
        # If private key starts with 0x, it's fine
        account = Account.from_key(private_key)

        # Encrypt using user's password (same as your wallet creation flow)
        encrypted_keystore = account.encrypt(password)

        # Convert to JSON string for DB storage
        keystore_json = json.dumps(encrypted_keystore)

        return {
            "address": account.address,
            "keystore_json": keystore_json
        }

    except Exception as e:
        raise Exception(f"Encryption failed: {str(e)}")

private_key = ""
password = "Paves@123"

result = encrypt_existing_private_key(private_key, password)

print("Wallet Address:", result["address"])
print("Encrypted JSON:", result["keystore_json"])