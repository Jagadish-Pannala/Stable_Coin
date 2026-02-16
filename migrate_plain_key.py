import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from eth_account import Account

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def migrate_wallets():
    db = SessionLocal()

    try:
        result = db.execute(text("""
            SELECT tenant_id, customer_id, password, encrypted_private_key
            FROM bank_customer_details
            WHERE is_wallet = 1
        """))

        users = result.fetchall()

        print(f"Found {len(users)} users to migrate")

        for user in users:
            tenant_id = user.tenant_id
            customer_id = user.customer_id
            password = user.password
            plain_private_key = user.encrypted_private_key

            try:
                print(f"Migrating customer_id: {customer_id}")

                if not plain_private_key:
                    print("Skipping: No private key")
                    continue

                # Create account from plain private key
                account = Account.from_key(plain_private_key)

                # Encrypt using user password
                encrypted_keystore = account.encrypt(password)

                keystore_json = json.dumps(encrypted_keystore)

                # Update record
                db.execute(text("""
                    UPDATE bank_customer_details
                    SET encrypted_private_key = :keystore
                    WHERE tenant_id = :tenant_id
                    AND customer_id = :customer_id
                """), {
                    "keystore": keystore_json,
                    "tenant_id": tenant_id,
                    "customer_id": customer_id
                })

                db.commit()
                print(f"✅ Migrated {customer_id}")

            except Exception as e:
                print(f"❌ Failed for {customer_id}: {str(e)}")
                db.rollback()

        print("🎉 Migration completed")

    finally:
        db.close()


if __name__ == "__main__":
    migrate_wallets()
