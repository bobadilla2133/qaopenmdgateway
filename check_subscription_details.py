#!/usr/bin/env python3
import websocket
import json
import time
import threading

class DetailedSubscriptionChecker:
    def __init__(self, url="ws://localhost:7799"):
        self.url = url
        self.ws = None
        self.session_id = None
        
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')
            timestamp = data.get('timestamp', 'N/A')
            
            print(f"\n📨 [{time.strftime('%H:%M:%S')}] 消息类型: {msg_type}")
            
            if msg_type == 'welcome':
                self.session_id = data.get('session_id', 'unknown')
                ctp_connected = data.get('ctp_connected', False)
                print(f"   会话ID: {self.session_id}")
                print(f"   CTP状态: {'✅ 已连接' if ctp_connected else '❌ 未连接'}")
                
            elif msg_type == 'subscribe_response':
                status = data.get('status', 'unknown')
                count = data.get('subscribed_count', 0)
                connection_id = data.get('connection_id', 'unknown')  # 看是否有此字段
                broker_id = data.get('broker_id', 'unknown')  # 看是否有此字段
                
                print(f"   状态: {status}")
                print(f"   订阅数量: {count}")
                if connection_id != 'unknown':
                    print(f"   处理连接: {connection_id}")
                if broker_id != 'unknown':
                    print(f"   Broker ID: {broker_id}")
                    
            elif msg_type == 'error':
                error_msg = data.get('message', 'unknown')
                connection_id = data.get('connection_id', 'N/A')
                print(f"   ❌ 错误: {error_msg}")
                if connection_id != 'N/A':
                    print(f"   错误连接: {connection_id}")
                    
            elif msg_type == 'market_data':
                instrument = data.get('instrument_id', 'unknown')
                price = data.get('last_price', 'N/A')
                volume = data.get('volume', 'N/A')
                connection_id = data.get('connection_id', 'unknown')
                broker_id = data.get('broker_id', 'unknown')
                
                print(f"   合约: {instrument}")
                print(f"   价格: {price}, 成交量: {volume}")
                if connection_id != 'unknown':
                    print(f"   数据来源连接: {connection_id}")
                if broker_id != 'unknown':
                    print(f"   数据来源Broker: {broker_id}")
                    
            elif msg_type == 'subscription_status':
                # 可能的订阅状态消息
                print(f"   订阅状态详情: {json.dumps(data, indent=4, ensure_ascii=False)}")
                
            else:
                # 显示完整消息以查看所有可用字段
                print(f"   完整消息: {json.dumps(data, indent=4, ensure_ascii=False)}")
                
        except Exception as e:
            print(f"❌ 处理消息失败: {e}")
            print(f"   原始消息: {message}")
    
    def on_error(self, ws, error):
        print(f"❌ WebSocket错误: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print(f"🔌 连接关闭: {close_status_code}")
        
    def on_open(self, ws):
        print("✅ WebSocket连接成功")
        print("🔍 开始详细订阅测试...\n")
        
        # 测试多个不同的合约，看哪个broker处理
        test_instruments = [
            "rb2601",  # 螺纹钢
            "cu2601",  # 铜
            "au2512",  # 黄金
            "ag2512",  # 白银
            "zn2601"   # 锌
        ]
        
        for i, instrument in enumerate(test_instruments):
            time.sleep(1)  # 间隔1秒
            subscribe_msg = {
                "action": "subscribe",
                "instruments": [instrument]
            }
            print(f"📤 [{time.strftime('%H:%M:%S')}] 订阅合约 {i+1}: {instrument}")
            ws.send(json.dumps(subscribe_msg))
    
    def start_test(self, duration=30):
        print(f"🚀 开始详细订阅检查 ({duration}秒)")
        print(f"🔗 连接到: {self.url}")
        print("=" * 60)
        
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # 设置定时器
        def stop_after_duration():
            time.sleep(duration)
            print(f"\n⏰ 测试时间结束 ({duration}秒)")
            self.ws.close()
        
        timer = threading.Thread(target=stop_after_duration)
        timer.daemon = True
        timer.start()
        
        # 定期发送状态查询（如果支持的话）
        def periodic_status_check():
            time.sleep(10)  # 10秒后开始
            while timer.is_alive():
                try:
                    # 尝试获取订阅状态
                    status_msg = {"action": "get_subscription_status"}
                    print(f"\n📊 [{time.strftime('%H:%M:%S')}] 查询订阅状态...")
                    self.ws.send(json.dumps(status_msg))
                    time.sleep(10)  # 每10秒查询一次
                except:
                    pass
        
        status_thread = threading.Thread(target=periodic_status_check)
        status_thread.daemon = True
        status_thread.start()
        
        self.ws.run_forever()

if __name__ == "__main__":
    checker = DetailedSubscriptionChecker()
    checker.start_test(45)  # 运行45秒