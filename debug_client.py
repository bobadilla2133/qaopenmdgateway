#!/usr/bin/env python3
"""简单的WebSocket调试客户端"""

import websocket
import json
import sys

def on_message(ws, message):
    print(f"[消息] {message}")
    try:
        data = json.loads(message)
        if data.get('type') == 'welcome':
            # 发送订阅请求
            sub_msg = {"action": "subscribe", "instruments": ["rb2601"]}
            print(f"[发送] {json.dumps(sub_msg)}")
            ws.send(json.dumps(sub_msg))
    except Exception as e:
        print(f"[错误] 处理消息失败: {e}")

def on_error(ws, error):
    print(f"[错误] {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"[关闭] 状态: {close_status_code}, 消息: {close_msg}")

def on_open(ws):
    print("[连接] WebSocket连接成功")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:7799"
    websocket.enableTrace(True)  # 启用调试输出
    ws = websocket.WebSocketApp(url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    print(f"[开始] 连接到 {url}")
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n[退出] 用户中断")
    except Exception as e:
        print(f"[异常] {e}")