"""
Redis Client - Handles caching for transaction history
"""

import os
import redis
import json
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for caching transaction data"""
    
    def __init__(self):
        """Initialize Redis connection"""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        redis_db = int(os.getenv("REDIS_DB", 0))
        
        try:
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                ssl=True,
                ssl_cert_reqs=None
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"✅ Redis connected: {redis_host}:{redis_port}")
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Redis initialization error: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and available"""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except:
            return False
    
    # ========== FULL CHAIN TRANSACTION CACHE ==========
    
    def get_full_chain_transactions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached full chain transaction list
        
        Returns:
            List of all transactions if cached, None if cache miss
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping cache read")
            return None
        
        try:
            cached_data = self.client.get("tx_history:all_chain")
            
            if cached_data:
                logger.info("✅ Cache HIT: Full chain transactions")
                return json.loads(cached_data)
            else:
                logger.info("❌ Cache MISS: Full chain transactions")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def set_full_chain_transactions(
        self,
        transactions: List[Dict[str, Any]],
        ttl: int = 30000  # 5 minutes default
    ) -> bool:
        """
        Cache full chain transaction list
        
        Args:
            transactions: List of all chain transactions
            ttl: Time to live in seconds (default: 300 = 5 minutes)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping cache write")
            return False
        
        try:
            serialized = json.dumps(transactions)
            self.client.setex(
                "tx_history:all_chain",
                ttl,
                serialized
            )
            logger.info(f"✅ Cached full chain transactions (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def invalidate_full_chain_cache(self) -> bool:
        """
        Delete the full chain transaction cache
        Called when ANY transaction occurs
        
        Returns:
            True if deleted, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping cache invalidation")
            return False
        
        try:
            deleted = self.client.delete("tx_history:all_chain")
            if deleted:
                logger.info("✅ Cache INVALIDATED: Full chain transactions")
            else:
                logger.info("ℹ️  No cache to invalidate")
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    # ========== HELPER METHODS ==========
    
    def get_cache_ttl(self) -> Optional[int]:
        """Get remaining TTL for full chain cache"""
        if not self.is_connected():
            return None
        
        try:
            ttl = self.client.ttl("tx_history:all_chain")
            return ttl if ttl > 0 else None
        except:
            return None
    
    def flush_all(self):
        """⚠️ DELETE ALL CACHE - Use only for testing/debugging"""
        if not self.is_connected():
            return False
        
        try:
            self.client.flushdb()
            logger.warning("🗑️  FLUSHED ALL REDIS CACHE")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSH error: {e}")
            return False

        # ========== WALLET BALANCE CACHE ==========

    def get_wallet_balance(self, address: str):
        if not self.is_connected():
            return None

        key = f"wallet:balance:{address}"
        try:
            data = self.client.get(key)
            if data:
                logger.info(f"✅ Cache HIT: Wallet balance {address}")
                return json.loads(data)
            logger.info(f"❌ Cache MISS: Wallet balance {address}")
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None


    def set_wallet_balance(self, address: str, balance_data: dict, ttl: int = 60):
        if not self.is_connected():
            return False

        key = f"wallet:balance:{address}"
        try:
            self.client.setex(key, ttl, json.dumps(balance_data))
            logger.info(f"💾 Cached wallet balance {address} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False


    def invalidate_wallet_balance(self, address: str):
        if not self.is_connected():
            return False

        key = f"wallet:balance:{address}"
        try:
            self.client.delete(key)
            logger.info(f"🗑️ Invalidated wallet balance cache {address}")
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
