#!/usr/bin/env python3
import websocket
import json
import time
import threading
try:
    import redis
    r = redis.Redis(host='192.168.2.27', port=6379, decode_responses=True, socket_timeout=5)
except ImportError:
    r = None

def check_redis():
    """检查Redis数据"""
    if not r:
        return
    try:
        keys = r.keys("market_data*")
        print(f"📊 Redis中有 {len(keys)} 个market_data key")
        if keys:
            # 显示最新的几个
            for key in keys[-3:]:
                if key.startswith("market_data_hash:"):
                    price = r.hget(key, "last_price")
                    time_str = r.hget(key, "update_time")
                    print(f"  💰 {key}: 价格={price}, 时间={time_str}")
                else:
                    data = r.get(key)
                    if data and len(data) < 200:
                        print(f"  📄 {key}: {data[:100]}")
    except Exception as e:
        print(f"❌ Redis检查失败: {e}")

def on_message(ws, message):
    try:
        data = json.loads(message)
        msg_type = data.get('type', 'unknown')
        
        if msg_type == 'market_data':
            instrument = data.get('instrument_id', 'unknown')
            price = data.get('last_price', 'N/A')
            volume = data.get('volume', 'N/A')
            update_time = data.get('update_time', 'N/A')
            print(f"💰 行情数据 {instrument}: 价格={price}, 量={volume}, 时间={update_time}")
            
            # 立即检查Redis
            print("🔍 检查Redis...")
            check_redis()
            
        elif msg_type == 'error':
            print(f"❌ 错误: {data.get('message', 'unknown')}")
        elif msg_type == 'subscribe_response':
            status = data.get('status', 'unknown')
            count = data.get('subscribed_count', 0)
            print(f"📋 订阅响应: {status}, 订阅数量={count}")
        elif msg_type == 'welcome':
            ctp_connected = data.get('ctp_connected', False)
            print(f"👋 连接成功, CTP状态: {'✅' if ctp_connected else '❌'}")
        else:
            print(f"📨 其他消息: {msg_type}")
            
    except Exception as e:
        print(f"❌ 处理消息失败: {e}")

def on_open(ws):
    print("✅ WebSocket连接成功")
    
    # 订阅多个测试合约
    test_contracts = ["rb2501", "rb2505", "cu2501", "au2412", "ag2412"]
    
    for contract in test_contracts:
        subscribe_msg = {
            "action": "subscribe", 
            "instruments": [contract]
        }
        print(f"📤 订阅: {contract}")
        ws.send(json.dumps(subscribe_msg))
        time.sleep(0.5)

def main():
    url = "ws://localhost:7799"
    print(f"🚀 连接到: {url}")
    
    # 检查初始Redis状态
    print("📊 初始Redis状态:")
    check_redis()
    
    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=lambda ws, error: print(f"❌ 错误: {error}"),
        on_close=lambda ws, code, msg: print(f"🔌 连接关闭"),
        on_open=on_open
    )
    
    # 运行60秒
    def stop_later():
        time.sleep(60)
        print("⏰ 测试时间结束")
        ws.close()
    
    timer = threading.Thread(target=stop_later)
    timer.daemon = True
    timer.start()
    
    # 定期检查Redis
    def redis_checker():
        time.sleep(10)  # 等10秒后开始检查
        while timer.is_alive():
            print("\n🔍 定期检查Redis...")
            check_redis()
            time.sleep(15)  # 每15秒检查一次
    
    if r:
        redis_thread = threading.Thread(target=redis_checker)
        redis_thread.daemon = True
        redis_thread.start()
    
    ws.run_forever()

if __name__ == "__main__":
    main()