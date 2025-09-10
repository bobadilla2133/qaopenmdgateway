#!/usr/bin/env python3
import websocket
import json
import threading
import time
import sys

# 添加Redis检查
try:
    import redis
    r = redis.Redis(host='192.168.2.27', port=6379, decode_responses=True, socket_timeout=5)
except ImportError:
    print("❌ 需要安装redis: pip3 install redis")
    sys.exit(1)

class WebSocketTest:
    def __init__(self, url="ws://localhost:7799"):
        self.url = url
        self.ws = None
        self.connected = False
        
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            print(f"📨 收到消息: {data.get('type', 'unknown')}")
            
            if data.get('type') == 'market_data':
                instrument = data.get('instrument_id', 'unknown')
                price = data.get('last_price', 'N/A')
                print(f"💰 {instrument}: {price}")
                
                # 立即检查Redis
                try:
                    redis_key = f"market_data:{instrument}"
                    redis_data = r.get(redis_key)
                    if redis_data:
                        print(f"✅ Redis中找到数据: {redis_key}")
                    else:
                        print(f"❌ Redis中未找到: {redis_key}")
                        
                    # 检查hash数据
                    hash_key = f"market_data_hash:{instrument}"
                    hash_data = r.hget(hash_key, "last_price")
                    if hash_data:
                        print(f"✅ Redis Hash中找到价格: {hash_data}")
                    else:
                        print(f"❌ Redis Hash中未找到: {hash_key}")
                        
                except Exception as e:
                    print(f"❌ Redis检查失败: {e}")
                    
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败: {message}")
        except Exception as e:
            print(f"❌ 处理消息失败: {e}")
    
    def on_error(self, ws, error):
        print(f"❌ WebSocket错误: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 WebSocket连接关闭")
        self.connected = False
        
    def on_open(self, ws):
        print("✅ WebSocket连接成功")
        self.connected = True
        
        # 订阅测试合约
        test_instruments = ["rb2501", "cu2501", "au2412"]
        for instrument in test_instruments:
            subscribe_msg = {
                "action": "subscribe",
                "instrument_id": instrument
            }
            ws.send(json.dumps(subscribe_msg))
            print(f"📤 订阅合约: {instrument}")
            time.sleep(0.1)
    
    def start(self):
        print(f"🚀 连接到: {self.url}")
        
        # 检查Redis连接
        try:
            r.ping()
            print("✅ Redis连接正常")
        except:
            print("❌ Redis连接失败")
            return
            
        # 启动WebSocket
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # 运行30秒
        def run_for_duration():
            time.sleep(30)
            print("⏰ 测试时间结束")
            self.ws.close()
            
        timer = threading.Thread(target=run_for_duration)
        timer.daemon = True
        timer.start()
        
        self.ws.run_forever()

if __name__ == "__main__":
    url = "ws://localhost:7799" if len(sys.argv) == 1 else sys.argv[1]
    test = WebSocketTest(url)
    test.start()