#!/usr/bin/env python3
import sys
import time
try:
    import redis
except ImportError:
    print("❌ 需要安装redis模块: pip3 install redis")
    sys.exit(1)

def check_redis():
    """检查Redis数据"""
    print("🔍 检查Redis数据...")
    
    try:
        # 连接Redis
        r = redis.Redis(host='192.168.2.27', port=6379, decode_responses=True, socket_timeout=5)
        r.ping()
        print("✅ Redis连接成功")
        
        # 检查所有market_data相关key
        keys = r.keys("market_data*")
        print(f"📊 找到 {len(keys)} 个market_data相关key")
        
        if keys:
            print("\n📋 前10个key:")
            for key in keys[:10]:
                print(f"  - {key}")
                
            # 检查第一个key的内容
            first_key = keys[0]
            if first_key.startswith("market_data_hash:"):
                data = r.hgetall(first_key)
                print(f"\n📄 {first_key} 内容:")
                for field, value in list(data.items())[:5]:
                    print(f"  {field}: {value}")
            else:
                data = r.get(first_key)
                print(f"\n📄 {first_key} 内容:")
                print(f"  {data[:200]}..." if len(str(data)) > 200 else data)
        else:
            print("❌ Redis中没有market_data相关数据")
            
            # 检查所有key
            all_keys = r.keys("*")
            print(f"📊 Redis中总共有 {len(all_keys)} 个key")
            if all_keys:
                print("前10个key:")
                for key in all_keys[:10]:
                    print(f"  - {key}")
                    
    except redis.ConnectionError:
        print("❌ Redis连接失败，请检查Redis服务是否启动")
    except Exception as e:
        print(f"❌ 检查失败: {e}")

def monitor_redis(duration=30):
    """监控Redis数据变化"""
    print(f"📡 监控Redis数据变化 {duration}秒...")
    
    try:
        r = redis.Redis(host='192.168.2.27', port=6379, decode_responses=True, socket_timeout=5)
        r.ping()
        
        initial_keys = set(r.keys("market_data*"))
        initial_count = len(initial_keys)
        print(f"初始market_data key数量: {initial_count}")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            time.sleep(3)
            current_keys = set(r.keys("market_data*"))
            current_count = len(current_keys)
            
            new_keys = current_keys - initial_keys
            if new_keys:
                print(f"🆕 发现新key: {list(new_keys)[:3]}")
            
            elapsed = int(time.time() - start_time)
            print(f"⏱️  {elapsed}s/{duration}s - key数量: {current_count}")
            
            initial_keys = current_keys
            
    except Exception as e:
        print(f"❌ 监控失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_redis(60)
    else:
        check_redis()