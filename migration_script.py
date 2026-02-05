
import pymysql
from datetime import datetime
import hashlib
import sys
from dotenv import load_dotenv
import os

load_dotenv()
HOST = os.getenv('DB_HOST')
PORT = int(os.getenv('DB_PORT', 3306))
USER = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')
OLD_DB_NAME = os.getenv('OLD_DB_NAME')
NEW_DB_NAME = os.getenv('NEW_DB_NAME')

# Database connection configurations
OLD_DB_CONFIG = {
    'host': HOST,
    'port': PORT,  # Add port if not default 3306
    'user': USER,
    'password': PASSWORD,
    'database': OLD_DB_NAME,
    'charset': 'utf8mb4',
    'connect_timeout': 30,  # Increase timeout
    'ssl': {'ssl_mode': 'REQUIRED'}  # Aiven requires SSL
}

NEW_DB_CONFIG = {
    'host': HOST,
    'port': PORT,  # Add port if not default 3306
    'user': USER,
    'password': PASSWORD,
    'database': NEW_DB_NAME,
    'charset': 'utf8mb4',
    'connect_timeout': 30,
    'ssl': {'ssl_mode': 'REQUIRED'}  # Aiven requires SSL
}

# Configuration
DEFAULT_TENANT_ID = 1
HASH_PASSWORDS = False  # Set to True if you want to hash passwords

def test_connection(config, db_name):
    """Test database connection"""
    try:
        print(f"\nTesting connection to {db_name}...")
        conn = pymysql.connect(**config)
        print(f"✓ Successfully connected to {db_name}")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Failed to connect to {db_name}")
        print(f"Error: {e}")
        return False

# def hash_password(password):
#     """Hash password using SHA256"""
#     return hashlib.sha256(password.encode()).hexdigest()

def migrate_users():
    old_conn = None
    new_conn = None
    
    try:
        # Test connections first
        if not test_connection(OLD_DB_CONFIG, "OLD DATABASE"):
            print("\n❌ Cannot connect to old database. Please check:")
            print("1. Host and port are correct")
            print("2. Username and password are correct")
            print("3. Your IP is whitelisted in Aiven")
            print("4. SSL settings are correct")
            return
        
        if not test_connection(NEW_DB_CONFIG, "NEW DATABASE"):
            print("\n❌ Cannot connect to new database. Aborting.")
            return
        
        print("\n" + "="*50)
        print("Starting migration...")
        print("="*50)
        
        # Connect to old database
        old_conn = pymysql.connect(**OLD_DB_CONFIG)
        old_cursor = old_conn.cursor(pymysql.cursors.DictCursor)
        
        # Connect to new database
        new_conn = pymysql.connect(**NEW_DB_CONFIG)
        new_cursor = new_conn.cursor()
        
        # Fetch all users from old database
        print("\nFetching users from old database...")
        old_cursor.execute("""
            SELECT user_id, mail, name, password, is_active, wallet_address, private_key
            FROM user_wallets
        """)
        
        old_users = old_cursor.fetchall()
        
        print(f"Found {len(old_users)} users to migrate\n")
        
        # Insert into new database
        insert_query = """
            INSERT INTO bank_customer_details (
                tenant_id,
                customer_id,
                mail,
                name,
                phone_number,
                bank_account_number,
                password,
                is_active,
                wallet_address,
                private_key,
                is_wallet,
                created_at,
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        migrated_count = 0
        skipped_count = 0
        
        for user in old_users:
            try:
                # Prepare data for new schema
                tenant_id = DEFAULT_TENANT_ID
                customer_id = str(user['user_id'])
                mail = user['mail']
                name = user['name']
                phone_number = None
                bank_account_number = None
                password = user['password']  # No hashing since we're migrating existing passwords
                is_active = user['is_active']
                wallet_address = user['wallet_address']
                private_key = user['private_key']
                is_wallet = 1 if wallet_address else 0
                created_at = datetime.now()
                updated_at = datetime.now()
                
                # Insert into new database
                new_cursor.execute(insert_query, (
                    tenant_id,
                    customer_id,
                    mail,
                    name,
                    phone_number,
                    bank_account_number,
                    password,
                    is_active,
                    wallet_address,
                    private_key,
                    is_wallet,
                    created_at,
                    updated_at
                ))
                
                migrated_count += 1
                print(f"✓ Migrated user: {mail} (ID: {customer_id})")
                
            except pymysql.IntegrityError as e:
                skipped_count += 1
                print(f"✗ Skipped user {user['mail']}: {e}")
                continue
            except Exception as e:
                skipped_count += 1
                print(f"✗ Error migrating user {user.get('mail', 'unknown')}: {e}")
                continue
        
        # Commit the transaction
        new_conn.commit()
        
        print(f"\n{'='*50}")
        print(f"Migration Summary:")
        print(f"Total users found: {len(old_users)}")
        print(f"Successfully migrated: {migrated_count}")
        print(f"Skipped/Failed: {skipped_count}")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        if new_conn:
            new_conn.rollback()
    
    finally:
        # Close connections
        if old_conn:
            old_conn.close()
        if new_conn:
            new_conn.close()

if __name__ == "__main__":
    print("User Migration Script")
    print("=" * 50)
    print(f"Password hashing: {'ENABLED' if HASH_PASSWORDS else 'DISABLED'}")
    
    # Update these values
    print("\n⚠️  IMPORTANT: Update the following in the script:")
    print("1. Database credentials (user, password)")
    print("2. Database names")
    print("3. Old table name in the SELECT query")
    print("4. Port number (usually 25060 for Aiven)")
    print("5. DEFAULT_TENANT_ID")
    
    confirm = input("\nHave you updated all configuration? (yes/no): ")
    
    if confirm.lower() == 'yes':
        migrate_users()
    else:
        print("Please update the configuration first.")