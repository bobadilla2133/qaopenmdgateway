#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantAxis Market Data WebSocket 测试客户端
连接到qactpmdgateway服务器，订阅行情数据并打印接收到的行情信息
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MarketDataClient:
    """市场行情数据WebSocket客户端"""
    
    def __init__(self, server_url: str = "ws://localhost:7799"):
        """
        初始化客户端
        
        Args:
            server_url: WebSocket服务器地址
        """
        self.server_url = server_url
        self.websocket = None
        self.session_id = None
        self.is_running = False
        self.subscribed_instruments = set()
        self.print_market_data = True  # 控制是否打印行情数据
        
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            logger.info(f"正在连接到服务器: {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.is_running = True
            logger.info("✅ WebSocket连接建立成功")
            return True
        except Exception as e:
            logger.error(f"❌ 连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.websocket:
            self.is_running = False
            await self.websocket.close()
            logger.info("🔌 WebSocket连接已断开")
    
    async def send_message(self, message: Dict[str, Any]):
        """
        发送消息到服务器
        
        Args:
            message: 要发送的消息字典
        """
        if not self.websocket:
            logger.error("❌ WebSocket未连接")
            return
        
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            logger.info(f"📤 发送消息: {message_json}")
            await self.websocket.send(message_json)
        except Exception as e:
            logger.error(f"❌ 发送消息失败: {e}")
    
    async def subscribe_instruments(self, instruments: list):
        """
        订阅合约行情
        
        Args:
            instruments: 要订阅的合约代码列表
        """
        message = {
            "action": "subscribe",
            "instruments": instruments
        }
        await self.send_message(message)
        self.subscribed_instruments.update(instruments)
    
    async def unsubscribe_instruments(self, instruments: list):
        """
        取消订阅合约行情
        
        Args:
            instruments: 要取消订阅的合约代码列表
        """
        message = {
            "action": "unsubscribe", 
            "instruments": instruments
        }
        await self.send_message(message)
        for instrument in instruments:
            self.subscribed_instruments.discard(instrument)
    
    async def list_instruments(self):
        """查询所有可用合约"""
        message = {"action": "list"}
        await self.send_message(message)
    
    async def search_instruments(self, pattern: str):
        """
        搜索合约
        
        Args:
            pattern: 搜索模式
        """
        message = {
            "action": "search",
            "pattern": pattern
        }
        await self.send_message(message)
    
    def format_market_data(self, data: Dict[str, Any]) -> str:
        """
        格式化行情数据为易读的字符串
        
        Args:
            data: 行情数据字典
            
        Returns:
            格式化后的字符串
        """
        try:
            return f"""
🚀 【实时行情】{data.get('instrument_id', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 时间: {data.get('trading_day', 'N/A')} {data.get('update_time', 'N/A')}.{data.get('update_millisec', 0):03d}
💰 最新价: {data.get('last_price', 0.0):.2f} | 昨结算: {data.get('pre_settlement_price', 0.0):.2f}
📈 开盘价: {data.get('open_price', 0.0):.2f} | 最高价: {data.get('highest_price', 0.0):.2f} | 最低价: {data.get('lowest_price', 0.0):.2f}
📊 成交量: {data.get('volume', 0):,} | 成交额: {data.get('turnover', 0.0):,.0f}
🏦 持仓量: {data.get('open_interest', 0.0):,.0f}
📏 涨停价: {data.get('upper_limit_price', 0.0):.2f} | 跌停价: {data.get('lower_limit_price', 0.0):.2f}
📋 买一价: {data.get('bid_price1', 0.0):.2f}({data.get('bid_volume1', 0)}) | 卖一价: {data.get('ask_price1', 0.0):.2f}({data.get('ask_volume1', 0)})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        except Exception as e:
            logger.error(f"❌ 格式化行情数据失败: {e}")
            return f"📊 行情数据: {data}"
    
    def format_message(self, message_type: str, data: Dict[str, Any]) -> str:
        """
        根据消息类型格式化消息
        
        Args:
            message_type: 消息类型
            data: 消息数据
            
        Returns:
            格式化后的字符串
        """
        if message_type == "welcome":
            return f"""
🎉 【欢迎】连接成功!
🆔 会话ID: {data.get('session_id', 'N/A')}
🔗 CTP连接状态: {'✅ 已连接' if data.get('ctp_connected', False) else '❌ 未连接'}
⏱️  时间戳: {datetime.fromtimestamp(data.get('timestamp', 0) / 1000)}"""
        
        elif message_type == "subscribe_response":
            status = data.get('status', 'unknown')
            status_icon = '✅' if status == 'success' else '❌'
            return f"{status_icon} 【订阅响应】状态: {status}, 订阅数量: {data.get('subscribed_count', 0)}"
        
        elif message_type == "unsubscribe_response":
            status = data.get('status', 'unknown')
            status_icon = '✅' if status == 'success' else '❌'
            return f"{status_icon} 【取消订阅响应】状态: {status}, 取消数量: {data.get('unsubscribed_count', 0)}"
        
        elif message_type == "instrument_list":
            instruments = data.get('instruments', [])
            count = data.get('total_count', len(instruments))
            return f"📋 【合约列表】总数: {count}, 前10个: {instruments[:10]}"
        
        elif message_type == "search_result":
            instruments = data.get('instruments', [])
            pattern = data.get('pattern', 'N/A')
            count = data.get('match_count', len(instruments))
            return f"🔍 【搜索结果】模式: '{pattern}', 匹配数量: {count}, 结果: {instruments}"
        
        elif message_type == "error":
            return f"❌ 【错误】{data.get('message', '未知错误')}"
        
        else:
            return f"📨 【{message_type}】{data}"
    
    async def handle_message(self, message: str):
        """
        处理从服务器接收到的消息
        
        Args:
            message: 接收到的消息字符串
        """
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')
            
            if message_type == 'welcome':
                self.session_id = data.get('session_id')
                print(self.format_message(message_type, data))
                
            elif message_type == 'market_data':
                # 行情数据根据print_market_data标志决定是否打印
                if self.print_market_data:
                    print(self.format_market_data(data))
                
            else:
                # 其他消息使用通用格式化
                print(self.format_message(message_type, data))
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}, 原始消息: {message}")
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
    
    async def listen(self):
        """监听服务器消息"""
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except ConnectionClosed:
            logger.warning("⚠️  服务器连接已关闭")
        except WebSocketException as e:
            logger.error(f"❌ WebSocket异常: {e}")
        except Exception as e:
            logger.error(f"❌ 监听消息异常: {e}")
        finally:
            self.is_running = False
    
    async def interactive_mode(self):
        """交互模式，允许用户输入命令"""
        print("""
🎮 【交互模式】可用命令:
  - 'sub <instruments>' : 订阅合约 (例: sub rb2601,i2501)
  - 'unsub <instruments>': 取消订阅 (例: unsub rb2601)
  - 'list'               : 查询所有合约
  - 'search <pattern>'   : 搜索合约 (例: search rb)
  - 'status'             : 显示当前状态
  - 'help'               : 显示帮助
  - 'quit' 或 'exit'     : 退出程序
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        
        while self.is_running:
            try:
                # 使用asyncio的输入方法
                cmd = await asyncio.get_event_loop().run_in_executor(None, input, "📝 请输入命令: ")
                cmd = cmd.strip().lower()
                
                if cmd in ['quit', 'exit']:
                    print("👋 正在退出...")
                    break
                elif cmd == 'help':
                    print("""
🆘 【帮助信息】
  sub <instruments>  : 订阅合约，多个合约用逗号分隔
  unsub <instruments>: 取消订阅合约 
  list               : 查询所有可用合约
  search <pattern>   : 按模式搜索合约
  status             : 显示连接状态和已订阅合约
  help               : 显示此帮助信息
  quit/exit          : 退出程序""")
                elif cmd == 'status':
                    print(f"""
📊 【状态信息】
🔗 连接状态: {'✅ 已连接' if self.is_running else '❌ 未连接'}
🆔 会话ID: {self.session_id or 'N/A'}
📋 已订阅合约: {list(self.subscribed_instruments) if self.subscribed_instruments else '无'}""")
                elif cmd == 'list':
                    await self.list_instruments()
                elif cmd.startswith('search '):
                    pattern = cmd[7:].strip()
                    if pattern:
                        await self.search_instruments(pattern)
                    else:
                        print("❌ 请提供搜索模式")
                elif cmd.startswith('sub '):
                    instruments = [inst.strip() for inst in cmd[4:].split(',')]
                    if instruments and instruments[0]:
                        await self.subscribe_instruments(instruments)
                    else:
                        print("❌ 请提供要订阅的合约")
                elif cmd.startswith('unsub '):
                    instruments = [inst.strip() for inst in cmd[6:].split(',')]
                    if instruments and instruments[0]:
                        await self.unsubscribe_instruments(instruments)
                    else:
                        print("❌ 请提供要取消订阅的合约")
                elif cmd:
                    print(f"❌ 未知命令: '{cmd}', 输入 'help' 查看帮助")
                    
            except EOFError:
                print("\n👋 检测到EOF，正在退出...")
                break
            except KeyboardInterrupt:
                print("\n👋 检测到中断信号，正在退出...")
                break
            except Exception as e:
                logger.error(f"❌ 交互模式异常: {e}")


async def main():
    """主函数"""
    # 默认配置
    SERVER_URL = "ws://localhost:7799"
    TEST_INSTRUMENTS = ["rb2601"]  # 默认测试合约
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        SERVER_URL = sys.argv[1]
    if len(sys.argv) > 2:
        TEST_INSTRUMENTS = sys.argv[2].split(',')
    
    print(f"""
🚀 【QuantAxis行情客户端测试工具】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 服务器地址: {SERVER_URL}
📋 测试合约: {TEST_INSTRUMENTS}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    client = MarketDataClient(SERVER_URL)
    
    # 设置信号处理器
    def signal_handler(signum, frame):
        print(f"\n👋 接收到信号 {signum}，正在优雅退出...")
        client.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 连接服务器
        if not await client.connect():
            return 1
        
        # 等待欢迎消息
        await asyncio.sleep(1)
        
        # 自动订阅测试合约
        if TEST_INSTRUMENTS:
            print(f"🎯 自动订阅测试合约: {TEST_INSTRUMENTS}")
            await client.subscribe_instruments(TEST_INSTRUMENTS)
        
        # 创建任务
        listen_task = asyncio.create_task(client.listen())
        interactive_task = asyncio.create_task(client.interactive_mode())
        
        # 等待任一任务完成
        done, pending = await asyncio.wait(
            [listen_task, interactive_task], 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        return 1
    finally:
        await client.disconnect()
    
    print("👋 程序已退出")
    return 0


if __name__ == "__main__":
    # 检查依赖
    try:
        import websockets
    except ImportError:
        print("""
❌ 缺少依赖库 'websockets'
请安装: pip install websockets

或者使用完整安装:
pip install websockets asyncio
""")
        sys.exit(1)
    
    # 运行主程序
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
        sys.exit(0)