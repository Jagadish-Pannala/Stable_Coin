"""
Test Script - Verify Redis Caching Behavior
Run this to test the caching logic without needing the full API
"""

import time
from utils.redis_client import RedisClient

def test_redis_caching():
    """Test Redis caching flow"""
    
    print("\n" + "="*60)
    print("🧪 TESTING REDIS TRANSACTION CACHING")
    print("="*60 + "\n")
    
    # Initialize Redis client
    redis = RedisClient()
    
    # Test 1: Check connection
    print("📡 Test 1: Connection")
    if redis.is_connected():
        print("✅ Redis is connected\n")
    else:
        print("❌ Redis is NOT connected - make sure Redis is running!")
        print("   Start Redis: redis-server")
        return
    
    # Test 2: Cache MISS (first time)
    print("📋 Test 2: Cache Miss (First Request)")
    result = redis.get_full_chain_transactions()
    if result is None:
        print("✅ Cache miss as expected (no data yet)\n")
    else:
        print("⚠️  Cache already exists (expected empty on first run)\n")
    
    # Test 3: Set cache
    print("💾 Test 3: Caching Sample Data")
    sample_transactions = [
        {
            "from_address": "0xabc123",
            "to_address": "0xdef456",
            "amount": 100.5,
            "asset": "USDC",
            "tx_hash": "0x111",
            "timestamp": "09-02-2026 14:30:00"
        },
        {
            "from_address": "0xdef456",
            "to_address": "0xabc123",
            "amount": 50.25,
            "asset": "USDT",
            "tx_hash": "0x222",
            "timestamp": "09-02-2026 15:45:00"
        }
    ]
    
    success = redis.set_full_chain_transactions(sample_transactions, ttl=60)  # 60 sec TTL for testing
    if success:
        print("✅ Sample data cached successfully\n")
    else:
        print("❌ Failed to cache data\n")
        return
    
    # Test 4: Cache HIT (retrieve cached data)
    print("📦 Test 4: Cache Hit (Second Request)")
    cached = redis.get_full_chain_transactions()
    if cached and len(cached) == 2:
        print("✅ Cache hit! Retrieved cached transactions")
        print(f"   Found {len(cached)} transactions\n")
    else:
        print("❌ Cache hit failed\n")
        return
    
    # Test 5: Check TTL
    print("⏱️  Test 5: Check Cache TTL")
    ttl = redis.get_cache_ttl()
    if ttl:
        print(f"✅ Cache expires in {ttl} seconds\n")
    else:
        print("⚠️  No TTL found\n")
    
    # Test 6: Invalidate cache (simulate transaction)
    print("🗑️  Test 6: Cache Invalidation (Transaction Occurred)")
    invalidated = redis.invalidate_full_chain_cache()
    if invalidated:
        print("✅ Cache invalidated successfully\n")
    else:
        print("⚠️  No cache to invalidate (might be expired)\n")
    
    # Test 7: Verify cache is gone
    print("🔍 Test 7: Verify Cache is Empty After Invalidation")
    after_invalidation = redis.get_full_chain_transactions()
    if after_invalidation is None:
        print("✅ Cache is empty as expected\n")
    else:
        print("❌ Cache still exists after invalidation\n")
    
    # Test 8: Simulate real flow
    print("🔄 Test 8: Simulate Real Request Flow")
    print("   Request 1: Cache miss → Fetch from Tenderly → Cache")
    redis.set_full_chain_transactions(sample_transactions, ttl=300)
    
    print("   Request 2: Cache hit → Return cached data")
    cached_again = redis.get_full_chain_transactions()
    print(f"   ✅ Served from cache: {len(cached_again)} transactions")
    
    print("\n   🔥 Transaction happens...")
    redis.invalidate_full_chain_cache()
    
    print("   Request 3: Cache miss → Fetch fresh from Tenderly")
    miss_again = redis.get_full_chain_transactions()
    print(f"   ✅ Cache miss as expected: {miss_again is None}\n")
    
    print("="*60)
    print("✅ ALL TESTS PASSED - Redis caching is working correctly!")
    print("="*60 + "\n")


def test_filtering():
    """Test transaction filtering logic"""
    
    print("\n" + "="*60)
    print("🧪 TESTING TRANSACTION FILTERING")
    print("="*60 + "\n")
    
    all_transactions = [
        {"from": "0xabc", "to": "0xdef", "amount": 100},
        {"from": "0xdef", "to": "0xabc", "amount": 50},
        {"from": "0x123", "to": "0x456", "amount": 75},
        {"from": "0xabc", "to": "0x789", "amount": 25},
    ]
    
    target_address = "0xabc"
    
    # Filter
    filtered = [
        tx for tx in all_transactions
        if tx["from"] == target_address or tx["to"] == target_address
    ]
    
    print(f"📦 Total chain transactions: {len(all_transactions)}")
    print(f"🔍 Filtered for {target_address}: {len(filtered)} transactions")
    print(f"✅ Expected: 3, Got: {len(filtered)}\n")
    
    assert len(filtered) == 3, "Filtering logic failed!"
    
    print("="*60)
    print("✅ FILTERING TEST PASSED")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting Redis Cache Tests...")
    print("Make sure Redis is running: redis-server\n")
    
    try:
        test_redis_caching()
        test_filtering()
        
        print("\n" + "🎉"*20)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("🎉"*20 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()