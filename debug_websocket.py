#!/usr/bin/env python3
import websocket
import json
import time

def on_message(ws, message):
    try:
        data = json.loads(message)
        msg_type = data.get('type', 'unknown')
        print(f"📨 消息类型: {msg_type}")
        
        if msg_type == 'error':
            print(f"❌ 错误信息: {data.get('message', 'no message')}")
            print(f"   详细: {json.dumps(data, indent=2, ensure_ascii=False)}")
        elif msg_type == 'welcome':
            print(f"👋 欢迎消息: {data}")
        elif msg_type == 'market_data':
            instrument = data.get('instrument_id', 'unknown')
            price = data.get('last_price', 'N/A')
            print(f"💰 行情数据 {instrument}: {price}")
        else:
            print(f"📋 完整消息: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {message}")
        print(f"   错误: {e}")
    except Exception as e:
        print(f"❌ 处理消息失败: {e}")

def on_error(ws, error):
    print(f"❌ WebSocket错误: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 连接关闭: {close_status_code}, {close_msg}")

def on_open(ws):
    print("✅ WebSocket连接成功")
    
    # 订阅一个合约 - 使用正确的格式
    subscribe_msg = {
        "action": "subscribe", 
        "instruments": ["rb2601"]
    }
    
    print(f"📤 发送订阅请求: {json.dumps(subscribe_msg)}")
    ws.send(json.dumps(subscribe_msg))

def main():
    url = "ws://localhost:7799"
    print(f"🚀 连接到: {url}")
    
    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error, 
        on_close=on_close,
        on_open=on_open
    )
    
    # 运行10秒
    import threading
    def stop_after_delay():
        time.sleep(10)
        print("⏰ 停止测试")
        ws.close()
    
    timer = threading.Thread(target=stop_after_delay)
    timer.daemon = True
    timer.start()
    
    ws.run_forever()

if __name__ == "__main__":
    main()