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
    'port': PORT,
    'user': USER,
    'password': PASSWORD,
    'database': OLD_DB_NAME,
    'charset': 'utf8mb4',
    'connect_timeout': 30,
    'ssl': {'ssl_mode': 'REQUIRED'}
}

NEW_DB_CONFIG = {
    'host': HOST,
    'port': PORT,
    'user': USER,
    'password': PASSWORD,
    'database': NEW_DB_NAME,
    'charset': 'utf8mb4',
    'connect_timeout': 30,
    'ssl': {'ssl_mode': 'REQUIRED'}
}

# Configuration
TENANT_NAME = "Tenderly Virtual Testnets"
RPC_URL = os.getenv("TENDERLY_VIRTUAL_TESTNET_RPC")  # Update with actual RPC
CHAIN_ID = 1  # Update with actual chain ID
OLD_TABLE_NAME = "user_wallets"
HASH_PASSWORDS = False

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

def get_or_create_tenant(cursor, conn):
    """Get existing tenant or create new one"""
    try:
        # Check if tenant already exists
        cursor.execute(
            "SELECT id FROM tenant_details WHERE tenant_name = %s",
            (TENANT_NAME,)
        )
        result = cursor.fetchone()
        
        if result:
            tenant_id = result[0]
            print(f"✓ Found existing tenant '{TENANT_NAME}' (ID: {tenant_id})")
            return tenant_id
        
        # Create new tenant
        cursor.execute("""
            INSERT INTO tenant_details (tenant_name, rpc_url, chain_id, is_active)
            VALUES (%s, %s, %s, %s)
        """, (TENANT_NAME, RPC_URL, CHAIN_ID, True))
        
        conn.commit()
        tenant_id = cursor.lastrowid
        print(f"✓ Created new tenant '{TENANT_NAME}' (ID: {tenant_id})")
        return tenant_id
        
    except Exception as e:
        print(f"✗ Error with tenant: {e}")
        raise

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
        
        # Connect to databases
        old_conn = pymysql.connect(**OLD_DB_CONFIG)
        old_cursor = old_conn.cursor(pymysql.cursors.DictCursor)
        
        new_conn = pymysql.connect(**NEW_DB_CONFIG)
        new_cursor = new_conn.cursor()
        
        # Get or create tenant
        print("\nChecking tenant...")
        tenant_id = get_or_create_tenant(new_cursor, new_conn)
        
        # Fetch all users from old database
        print("\nFetching users from old database...")
        old_cursor.execute(f"""
            SELECT user_id, mail, name, password, is_active, wallet_address, private_key
            FROM {OLD_TABLE_NAME}
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
                encrypted_private_key,
                fiat_bank_balance,
                is_wallet,
                created_at,
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        migrated_count = 0
        skipped_count = 0
        errors = []
        
        for user in old_users:
            try:
                # Prepare data for new schema
                customer_id = str(user['user_id'])
                mail = user['mail']
                name = user['name']
                phone_number = None
                bank_account_number = None
                password = user['password']
                is_active = user['is_active']
                wallet_address = user['wallet_address']
                encrypted_private_key = user['private_key']
                fiat_bank_balance = 0.00
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
                    encrypted_private_key,
                    fiat_bank_balance,
                    is_wallet,
                    created_at,
                    updated_at
                ))
                
                migrated_count += 1
                print(f"✓ Migrated user: {mail} (ID: {customer_id})")
                
            except pymysql.IntegrityError as e:
                skipped_count += 1
                error_msg = f"User {user.get('mail', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ Skipped - {error_msg}")
                continue
            except Exception as e:
                skipped_count += 1
                error_msg = f"User {user.get('mail', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ Error - {error_msg}")
                continue
        
        # Commit the transaction
        new_conn.commit()
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"Migration Summary:")
        print(f"{'='*50}")
        print(f"Tenant: {TENANT_NAME} (ID: {tenant_id})")
        print(f"Total users found: {len(old_users)}")
        print(f"Successfully migrated: {migrated_count}")
        print(f"Skipped/Failed: {skipped_count}")
        print(f"{'='*50}")
        
        if errors:
            print(f"\n{'='*50}")
            print("Error Details:")
            print(f"{'='*50}")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  • {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        if new_conn:
            new_conn.rollback()
    
    finally:
        # Close connections
        if old_conn:
            old_conn.close()
        if new_conn:
            new_conn.close()

def verify_migration():
    """Verify the migration results"""
    try:
        conn = pymysql.connect(**NEW_DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        print("\n" + "="*50)
        print("Verification Results:")
        print("="*50)
        
        # Check tenant
        cursor.execute("SELECT * FROM tenant_details WHERE tenant_name = %s", (TENANT_NAME,))
        tenant = cursor.fetchone()
        if tenant:
            print(f"\n✓ Tenant Found:")
            print(f"  ID: {tenant['id']}")
            print(f"  Name: {tenant['tenant_name']}")
            print(f"  RPC URL: {tenant['rpc_url']}")
            print(f"  Chain ID: {tenant['chain_id']}")
            print(f"  Active: {tenant['is_active']}")
        
        # Check migrated users
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN wallet_address IS NOT NULL THEN 1 ELSE 0 END) as with_wallet
            FROM bank_customer_details
            WHERE tenant_id = %s
        """, (tenant['id'],))
        
        stats = cursor.fetchone()
        print(f"\n✓ Migrated Users:")
        print(f"  Total: {stats['total']}")
        print(f"  Active: {stats['active']}")
        print(f"  With Wallet: {stats['with_wallet']}")
        
        # Sample users
        cursor.execute("""
            SELECT customer_id, mail, name, wallet_address, is_active
            FROM bank_customer_details
            WHERE tenant_id = %s
            LIMIT 5
        """, (tenant['id'],))
        
        sample_users = cursor.fetchall()
        if sample_users:
            print(f"\n✓ Sample Users:")
            for user in sample_users:
                print(f"  • {user['name']} ({user['mail']}) - Wallet: {user['wallet_address'][:10] if user['wallet_address'] else 'None'}...")
        
        conn.close()
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")

if __name__ == "__main__":
    print("="*50)
    print("User Migration Script")
    print("="*50)
    print(f"\nConfiguration:")
    print(f"  Host: {HOST}")
    print(f"  Port: {PORT}")
    print(f"  Old DB: {OLD_DB_NAME}")
    print(f"  New DB: {NEW_DB_NAME}")
    print(f"  Old Table: {OLD_TABLE_NAME}")
    print(f"  Tenant: {TENANT_NAME}")
    print(f"  RPC URL: {RPC_URL}")
    print(f"  Chain ID: {CHAIN_ID}")
    print(f"  Password Hashing: {'ENABLED' if HASH_PASSWORDS else 'DISABLED'}")
    
    confirm = input("\nProceed with migration? (yes/no): ")
    
    if confirm.lower() == 'yes':
        migrate_users()
        
        verify = input("\nRun verification? (yes/no): ")
        if verify.lower() == 'yes':
            verify_migration()
    else:
        print("\nMigration cancelled.")