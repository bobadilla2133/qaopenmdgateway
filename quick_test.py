#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 连接WebSocket并订阅rb2601
"""

import json
import time
import sys
import threading
from datetime import datetime

try:
    import websocket
except ImportError:
    print("❌ 请先安装: pip3 install websocket-client")
    sys.exit(1)


def on_message(ws, message):
    """处理消息"""
    try:
        data = json.loads(message)
        msg_type = data.get('type', 'unknown')
        
        if msg_type == 'welcome':
            print(f"✅ 连接成功! 会话ID: {data.get('session_id')}")
            # 订阅rb2601
            subscribe_msg = {
                "action": "subscribe",
                "instruments": ["rb2601"]
            }
            ws.send(json.dumps(subscribe_msg))
            print("📤 已发送订阅请求: rb2601")
            
        elif msg_type == 'market_data':
            instrument = data.get('instrument_id', 'N/A')
            last_price = data.get('last_price', 0.0)
            volume = data.get('volume', 0)
            time_str = f"{data.get('update_time', 'N/A')}.{data.get('update_millisec', 0):03d}"
            
            print(f"🚀 【{instrument}】价格: {last_price:.2f}, 成交量: {volume:,}, 时间: {time_str}")
            
        elif msg_type == 'subscribe_response':
            print(f"✅ 订阅响应: {data.get('status')} - {data.get('subscribed_count')} 个合约")
            
        elif msg_type == 'error':
            print(f"❌ 错误: {data.get('message')}")
            
    except Exception as e:
        print(f"❌ 处理消息异常: {e}")


def on_error(ws, error):
    print(f"❌ WebSocket错误: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"🔌 连接已关闭")


def on_open(ws):
    print(f"🔗 WebSocket连接已建立")
    print("⏳ 等待欢迎消息...")


def main():
    server_url = "ws://localhost:7799"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"""
🚀 【快速测试】连接到 {server_url}
📋 将自动订阅: rb2601
⏰ 按 Ctrl+C 停止
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    ws = websocket.WebSocketApp(
        server_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    try:
        print("🔄 开始连接...")
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在断开连接...")
        ws.close()
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return 1


if __name__ == "__main__":
    main()