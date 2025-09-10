#!/usr/bin/env python3
import websocket
import json
import time

def on_message(ws, message):
    try:
        data = json.loads(message)
        print(f"📨 {data.get('type', 'unknown')}: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ 处理消息失败: {e}")

def on_open(ws):
    print("✅ WebSocket连接成功")
    
    # 获取系统状态
    status_msg = {"action": "get_status"}
    ws.send(json.dumps(status_msg))
    print("📤 获取系统状态")
    
    time.sleep(1)
    
    # 列出所有可用合约
    list_msg = {"action": "list_instruments"}  
    ws.send(json.dumps(list_msg))
    print("📤 获取合约列表")
    
    time.sleep(1)
    
    # 搜索rb相关合约
    search_msg = {"action": "search_instruments", "pattern": "rb"}
    ws.send(json.dumps(search_msg))
    print("📤 搜索rb合约")

def main():
    url = "ws://localhost:7799"
    print(f"🚀 连接到: {url}")
    
    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=lambda ws, error: print(f"❌ 错误: {error}"),
        on_close=lambda ws, code, msg: print(f"🔌 连接关闭"),
        on_open=on_open
    )
    
    # 运行10秒
    import threading
    def stop_later():
        time.sleep(10)
        print("⏰ 结束")
        ws.close()
    
    timer = threading.Thread(target=stop_later)
    timer.daemon = True
    timer.start()
    
    ws.run_forever()

if __name__ == "__main__":
    main()