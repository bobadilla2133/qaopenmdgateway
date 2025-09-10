#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版本的WebSocket测试客户端
使用websocket-client库（同步版本）
"""

import json
import time
import threading
from datetime import datetime
import sys

try:
    import websocket
except ImportError:
    print("""
❌ 缺少依赖库 'websocket-client'
请安装: pip install websocket-client

或者使用异步版本:
python test_client.py
""")
    sys.exit(1)


class SimpleMarketDataClient:
    """简化的市场行情WebSocket客户端"""
    
    def __init__(self, server_url="ws://localhost:7799"):
        self.server_url = server_url
        self.ws = None
        self.is_connected = False
        self.session_id = None
        
    def on_message(self, ws, message):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')
            
            if msg_type == 'welcome':
                self.session_id = data.get('session_id')
                print(f"""
🎉 【连接成功】
🆔 会话ID: {data.get('session_id', 'N/A')}
🔗 CTP状态: {'✅ 已连接' if data.get('ctp_connected', False) else '❌ 未连接'}
⏰ 时间: {datetime.fromtimestamp(data.get('timestamp', 0) / 1000)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
                
            elif msg_type == 'market_data':
                self.print_market_data(data)
                
            elif msg_type == 'subscribe_response':
                status = data.get('status', 'unknown')
                count = data.get('subscribed_count', 0)
                print(f"✅ 【订阅成功】状态: {status}, 合约数: {count}")
                
            elif msg_type == 'error':
                print(f"❌ 【错误】{data.get('message', '未知错误')}")
                
            else:
                print(f"📨 【{msg_type}】{json.dumps(data, ensure_ascii=False, indent=2)}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
        except Exception as e:
            print(f"❌ 处理消息异常: {e}")
    
    def print_market_data(self, data):
        """打印格式化的行情数据"""
        instrument_id = data.get('instrument_id', 'N/A')
        last_price = data.get('last_price', 0.0)
        pre_settlement = data.get('pre_settlement_price', 0.0)
        volume = data.get('volume', 0)
        turnover = data.get('turnover', 0.0)
        open_interest = data.get('open_interest', 0.0)
        
        # 计算涨跌
        change = last_price - pre_settlement if last_price and pre_settlement else 0
        change_pct = (change / pre_settlement * 100) if pre_settlement else 0
        
        # 价格颜色（简化版）
        price_indicator = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        print(f"""
🚀 【{instrument_id}】实时行情 {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 最新价: {last_price:.2f} {price_indicator} ({change:+.2f}, {change_pct:+.2f}%)
📊 昨结算: {pre_settlement:.2f}
📈 开盘价: {data.get('open_price', 0.0):.2f} | 最高: {data.get('highest_price', 0.0):.2f} | 最低: {data.get('lowest_price', 0.0):.2f}
📋 成交量: {volume:,} | 成交额: {turnover:,.0f}
🏦 持仓量: {open_interest:,.0f}
📏 涨停: {data.get('upper_limit_price', 0.0):.2f} | 跌停: {data.get('lower_limit_price', 0.0):.2f}
📋 买一: {data.get('bid_price1', 0.0):.2f}({data.get('bid_volume1', 0)}) | 卖一: {data.get('ask_price1', 0.0):.2f}({data.get('ask_volume1', 0)})
⏰ 更新时间: {data.get('trading_day', 'N/A')} {data.get('update_time', 'N/A')}.{data.get('update_millisec', 0):03d}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
    
    def on_error(self, ws, error):
        """处理错误"""
        print(f"❌ WebSocket错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        self.is_connected = False
        print(f"🔌 连接已关闭 - 状态码: {close_status_code}, 消息: {close_msg}")
    
    def on_open(self, ws):
        """连接打开"""
        self.is_connected = True
        print(f"🔗 WebSocket连接已建立: {self.server_url}")
        
        # 等待1秒后自动订阅测试合约
        def auto_subscribe():
            time.sleep(1)
            instruments = ["rb2601"]  # 默认订阅rb2601
            print(f"🎯 自动订阅合约: {instruments}")
            self.subscribe(instruments)
            
        threading.Thread(target=auto_subscribe, daemon=True).start()
    
    def subscribe(self, instruments):
        """订阅合约"""
        if not self.is_connected:
            print("❌ 未连接到服务器")
            return
            
        message = {
            "action": "subscribe",
            "instruments": instruments
        }
        self.send_message(message)
    
    def unsubscribe(self, instruments):
        """取消订阅"""
        if not self.is_connected:
            print("❌ 未连接到服务器")
            return
            
        message = {
            "action": "unsubscribe",
            "instruments": instruments
        }
        self.send_message(message)
    
    def list_instruments(self):
        """查询合约列表"""
        message = {"action": "list"}
        self.send_message(message)
    
    def search_instruments(self, pattern):
        """搜索合约"""
        message = {
            "action": "search",
            "pattern": pattern
        }
        self.send_message(message)
    
    def send_message(self, message):
        """发送消息"""
        if not self.is_connected:
            print("❌ 未连接到服务器")
            return
            
        try:
            msg_json = json.dumps(message, ensure_ascii=False)
            print(f"📤 发送: {msg_json}")
            self.ws.send(msg_json)
        except Exception as e:
            print(f"❌ 发送失败: {e}")
    
    def connect(self):
        """连接服务器"""
        try:
            # 启用调试（可选）
            # websocket.enableTrace(True)
            
            self.ws = websocket.WebSocketApp(
                self.server_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            print(f"🚀 正在连接到: {self.server_url}")
            self.ws.run_forever()
            
        except KeyboardInterrupt:
            print("\n👋 用户中断，正在断开连接...")
            if self.ws:
                self.ws.close()
        except Exception as e:
            print(f"❌ 连接异常: {e}")


def interactive_mode(client):
    """交互模式"""
    print("""
🎮 【交互模式】可用命令 (输入 'help' 查看帮助):""")
    
    while True:
        try:
            cmd = input("\n📝 请输入命令: ").strip().lower()
            
            if cmd in ['quit', 'exit']:
                print("👋 正在退出...")
                if client.ws:
                    client.ws.close()
                break
                
            elif cmd == 'help':
                print("""
🆘 【命令帮助】
  sub <instruments>    : 订阅合约 (例: sub rb2601,i2501)
  unsub <instruments>  : 取消订阅 (例: unsub rb2601) 
  list                 : 查询所有合约
  search <pattern>     : 搜索合约 (例: search rb)
  help                 : 显示帮助
  quit/exit            : 退出程序
  
📝 示例:
  sub rb2601           : 订阅rb2601合约
  sub rb2601,i2501     : 订阅多个合约
  search rb            : 搜索包含'rb'的合约
  list                 : 显示所有合约""")
                
            elif cmd == 'list':
                client.list_instruments()
                
            elif cmd.startswith('search '):
                pattern = cmd[7:].strip()
                if pattern:
                    client.search_instruments(pattern)
                else:
                    print("❌ 请提供搜索模式")
                    
            elif cmd.startswith('sub '):
                instruments = [inst.strip() for inst in cmd[4:].split(',')]
                if instruments and instruments[0]:
                    client.subscribe(instruments)
                else:
                    print("❌ 请提供要订阅的合约")
                    
            elif cmd.startswith('unsub '):
                instruments = [inst.strip() for inst in cmd[6:].split(',')]
                if instruments and instruments[0]:
                    client.unsubscribe(instruments)
                else:
                    print("❌ 请提供要取消订阅的合约")
                    
            elif cmd:
                print(f"❌ 未知命令: '{cmd}', 输入 'help' 查看帮助")
                
        except EOFError:
            print("\n👋 检测到EOF，正在退出...")
            break
        except KeyboardInterrupt:
            print("\n👋 检测到中断，正在退出...")
            break
        except Exception as e:
            print(f"❌ 命令处理异常: {e}")


def main():
    """主函数"""
    # 解析命令行参数
    server_url = "ws://localhost:7799"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"""
🚀 【QuantAxis简化版行情测试客户端】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 服务器地址: {server_url}
📋 默认订阅: rb2601 (螺纹钢2601)
💡 提示: 连接成功后会自动订阅，也可使用交互命令
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    client = SimpleMarketDataClient(server_url)
    
    # 启动交互模式线程
    interactive_thread = threading.Thread(target=interactive_mode, args=(client,), daemon=True)
    interactive_thread.start()
    
    try:
        # 连接并保持运行
        client.connect()
    except Exception as e:
        print(f"❌ 程序异常: {e}")
    finally:
        print("👋 程序已退出")


if __name__ == "__main__":
    main()