#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis数据诊断工具
用于检查qactpmdgateway的Redis数据写入情况
"""

import redis
import json
import time
import sys
from datetime import datetime

class RedisDebugger:
    def __init__(self, host="192.168.2.27", port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        
    def connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.host, 
                port=self.port, 
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            print(f"✅ 成功连接到Redis: {self.host}:{self.port}")
            return True
        except redis.ConnectionError as e:
            print(f"❌ Redis连接失败: {e}")
            return False
        except Exception as e:
            print(f"❌ Redis连接异常: {e}")
            return False
            
    def check_market_data_keys(self):
        """检查市场数据相关的key"""
        print("\n🔍 检查市场数据相关key...")
        
        try:
            # 检查所有market_data相关的key
            market_data_keys = self.redis_client.keys("market_data:*")
            market_data_hash_keys = self.redis_client.keys("market_data_hash:*")
            
            print(f"📊 找到 {len(market_data_keys)} 个market_data key")
            print(f"📊 找到 {len(market_data_hash_keys)} 个market_data_hash key")
            
            if market_data_keys:
                print("\n📋 market_data keys:")
                for key in market_data_keys[:10]:  # 只显示前10个
                    print(f"  - {key}")
                if len(market_data_keys) > 10:
                    print(f"  ... 还有 {len(market_data_keys) - 10} 个")
                    
            if market_data_hash_keys:
                print("\n📋 market_data_hash keys:")
                for key in market_data_hash_keys[:10]:  # 只显示前10个
                    print(f"  - {key}")
                if len(market_data_hash_keys) > 10:
                    print(f"  ... 还有 {len(market_data_hash_keys) - 10} 个")
                    
            return market_data_keys, market_data_hash_keys
            
        except Exception as e:
            print(f"❌ 检查key失败: {e}")
            return [], []
            
    def check_specific_instrument(self, instrument_id):
        """检查特定合约的数据"""
        print(f"\n🔍 检查合约 {instrument_id} 的数据...")
        
        try:
            # 检查JSON数据
            json_key = f"market_data:{instrument_id}"
            json_data = self.redis_client.get(json_key)
            
            if json_data:
                print(f"✅ 找到JSON数据: {json_key}")
                try:
                    data = json.loads(json_data)
                    print(f"   最新价格: {data.get('last_price', 'N/A')}")
                    print(f"   更新时间: {data.get('update_time', 'N/A')}")
                    print(f"   成交量: {data.get('volume', 'N/A')}")
                except json.JSONDecodeError:
                    print("   ⚠️  JSON数据格式有误")
            else:
                print(f"❌ 未找到JSON数据: {json_key}")
                
            # 检查Hash数据
            hash_key = f"market_data_hash:{instrument_id}"
            hash_data = self.redis_client.hgetall(hash_key)
            
            if hash_data:
                print(f"✅ 找到Hash数据: {hash_key}")
                for field, value in hash_data.items():
                    print(f"   {field}: {value}")
            else:
                print(f"❌ 未找到Hash数据: {hash_key}")
                
        except Exception as e:
            print(f"❌ 检查合约数据失败: {e}")
            
    def monitor_real_time(self, duration=30):
        """实时监控Redis数据更新"""
        print(f"\n📡 实时监控Redis数据更新 ({duration}秒)...")
        
        try:
            # 记录初始key数量
            initial_keys = set(self.redis_client.keys("market_data*"))
            initial_count = len(initial_keys)
            print(f"初始key数量: {initial_count}")
            
            start_time = time.time()
            last_check_time = start_time
            
            while time.time() - start_time < duration:
                time.sleep(2)  # 每2秒检查一次
                
                current_keys = set(self.redis_client.keys("market_data*"))
                current_count = len(current_keys)
                
                # 检查新增的key
                new_keys = current_keys - initial_keys
                if new_keys:
                    print(f"\n🆕 发现新key (总数: {current_count}):")
                    for key in list(new_keys)[:5]:  # 只显示前5个
                        print(f"   + {key}")
                        # 显示数据内容
                        if key.startswith("market_data_hash:"):
                            data = self.redis_client.hget(key, "last_price")
                            if data:
                                print(f"     价格: {data}")
                    
                # 更新基准
                initial_keys = current_keys
                
                # 显示进度
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                print(f"⏱️  监控中... {elapsed}s/{duration}s (剩余{remaining}s, 当前key数量: {current_count})")
                
            print(f"\n✅ 监控完成，最终key数量: {len(current_keys)}")
            
        except KeyboardInterrupt:
            print("\n⏹️  监控已停止")
        except Exception as e:
            print(f"❌ 监控失败: {e}")
            
    def check_connection_info(self):
        """检查Redis连接信息"""
        print("\n🔧 Redis连接信息...")
        
        try:
            info = self.redis_client.info()
            print(f"Redis版本: {info.get('redis_version', 'N/A')}")
            print(f"连接客户端数: {info.get('connected_clients', 'N/A')}")
            print(f"使用内存: {info.get('used_memory_human', 'N/A')}")
            print(f"key总数: {info.get('db0', {}).get('keys', 0) if 'db0' in info else 0}")
            
        except Exception as e:
            print(f"❌ 获取Redis信息失败: {e}")

def main():
    print("🔍 QuantAxis Multi-CTP Gateway Redis诊断工具")
    print("=" * 50)
    
    # 解析命令行参数
    host = "192.168.2.27"
    port = 6379
    
    if len(sys.argv) > 1:
        if ":" in sys.argv[1]:
            host, port = sys.argv[1].split(":")
            port = int(port)
        else:
            host = sys.argv[1]
    
    debugger = RedisDebugger(host, port)
    
    # 连接Redis
    if not debugger.connect():
        print("无法连接到Redis，请检查:")
        print("1. Redis服务是否启动")
        print("2. 网络连接是否正常")
        print("3. 防火墙设置")
        sys.exit(1)
    
    try:
        # 检查连接信息
        debugger.check_connection_info()
        
        # 检查现有数据
        market_keys, hash_keys = debugger.check_market_data_keys()
        
        # 如果有数据，检查具体内容
        if market_keys or hash_keys:
            if market_keys:
                # 取第一个key的合约代码进行检查
                first_key = market_keys[0]
                instrument_id = first_key.replace("market_data:", "")
                debugger.check_specific_instrument(instrument_id)
        
        # 询问是否进行实时监控
        print(f"\n🤔 当前共有 {len(market_keys) + len(hash_keys)} 个市场数据key")
        
        if len(market_keys) == 0 and len(hash_keys) == 0:
            print("\n⚠️  当前Redis中没有市场数据!")
            print("可能的原因:")
            print("1. qactpmdgateway服务未启动")
            print("2. 未成功连接到CTP服务器")
            print("3. 没有订阅任何合约")
            print("4. Redis连接配置错误")
            
            choice = input("\n是否进行实时监控来检查数据写入? (y/N): ").lower()
            if choice in ['y', 'yes']:
                duration = 60  # 监控60秒
                debugger.monitor_real_time(duration)
        else:
            print("\n✅ 找到市场数据，Redis写入正常!")
            
    except KeyboardInterrupt:
        print("\n👋 诊断已停止")
    except Exception as e:
        print(f"\n❌ 诊断过程中发生错误: {e}")

if __name__ == "__main__":
    main()