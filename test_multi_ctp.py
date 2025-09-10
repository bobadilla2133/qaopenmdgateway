#!/usr/bin/env python3
"""
多CTP连接测试脚本
测试新的多CTP架构下的订阅分发功能
"""

import asyncio
import websockets
import json
import time
import sys
from typing import List, Dict, Any

class MultiCTPTester:
    def __init__(self, server_url: str = "ws://localhost:7799"):
        self.server_url = server_url
        self.websocket = None
        self.received_data = {}
        self.subscription_status = {}
        
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"✅ 连接到服务器: {self.server_url}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息到服务器"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            print(f"📤 发送消息: {message}")
    
    async def receive_messages(self):
        """接收服务器消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("🔌 连接已关闭")
        except Exception as e:
            print(f"❌ 接收消息错误: {e}")
    
    async def handle_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        msg_type = data.get("type", "unknown")
        
        if msg_type == "welcome":
            print(f"🎉 收到欢迎消息:")
            print(f"   Session ID: {data.get('session_id')}")
            print(f"   CTP状态: {'已连接' if data.get('ctp_connected') else '未连接'}")
            
        elif msg_type == "subscribe_response":
            print(f"📋 订阅响应:")
            print(f"   状态: {data.get('status')}")
            print(f"   已订阅数量: {data.get('subscribed_count')}")
            
        elif msg_type == "market_data":
            instrument_id = data.get("instrument_id")
            connection_id = data.get("connection_id", "unknown")
            
            if instrument_id not in self.received_data:
                self.received_data[instrument_id] = {
                    'count': 0,
                    'connections': set(),
                    'last_update': None
                }
            
            self.received_data[instrument_id]['count'] += 1
            self.received_data[instrument_id]['connections'].add(connection_id)
            self.received_data[instrument_id]['last_update'] = time.time()
            
            print(f"📊 [{connection_id}] {instrument_id}: 价格={data.get('last_price')}, "
                  f"成交量={data.get('volume')}, 时间={data.get('update_time')}")
                  
        elif msg_type == "error":
            print(f"❌ 服务器错误: {data.get('message')}")
            
        else:
            print(f"📥 其他消息类型: {msg_type}")
            
    async def test_mass_subscription(self, instruments: List[str]):
        """测试大量订阅"""
        print(f"\n🔄 开始测试大量订阅 ({len(instruments)} 个合约)")
        
        # 分批订阅以测试负载均衡
        batch_size = 100
        for i in range(0, len(instruments), batch_size):
            batch = instruments[i:i+batch_size]
            message = {
                "action": "subscribe",
                "instruments": batch
            }
            await self.send_message(message)
            await asyncio.sleep(1)  # 避免过快发送
            
        print(f"✅ 已发送所有订阅请求")
    
    async def monitor_connections(self, duration: int = 60):
        """监控连接状态"""
        print(f"\n👀 监控连接状态 ({duration} 秒)")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            # 显示统计信息
            total_messages = sum(data['count'] for data in self.received_data.values())
            active_instruments = len(self.received_data)
            all_connections = set()
            
            for data in self.received_data.values():
                all_connections.update(data['connections'])
            
            print(f"📈 实时统计:")
            print(f"   活跃合约: {active_instruments}")
            print(f"   总消息数: {total_messages}")
            print(f"   使用连接: {len(all_connections)} - {list(all_connections)}")
            
            await asyncio.sleep(10)
    
    async def test_failover(self):
        """测试故障转移（需要手动断开一个连接）"""
        print(f"\n🚨 故障转移测试")
        print("请手动断开一个CTP连接以测试故障转移...")
        
        # 记录故障前的连接状态
        before_connections = set()
        for data in self.received_data.values():
            before_connections.update(data['connections'])
        
        print(f"故障前连接: {before_connections}")
        
        # 监控30秒
        await asyncio.sleep(30)
        
        # 记录故障后的连接状态  
        after_connections = set()
        for data in self.received_data.values():
            after_connections.update(data['connections'])
            
        print(f"故障后连接: {after_connections}")
        
        if len(after_connections) < len(before_connections):
            print("✅ 检测到连接减少，故障转移可能已触发")
        else:
            print("⚠️ 未检测到连接变化")

async def main():
    # 创建测试合约列表
    test_instruments = []
    
    # 添加一些期货合约
    futures_codes = ['rb', 'i', 'j', 'jm', 'ZC', 'FG', 'MA', 'TA', 'bu', 'ru']
    months = ['2501', '2502', '2503', '2504', '2505']
    
    for code in futures_codes:
        for month in months:
            test_instruments.append(f"{code}{month}")
    
    # 添加一些股指期货
    index_codes = ['IF', 'IC', 'IH', 'IM', 'TF', 'T', 'TS']
    for code in index_codes:
        for month in months[:3]:  # 只用前3个月份
            test_instruments.append(f"{code}{month}")
    
    print(f"准备测试 {len(test_instruments)} 个合约")
    
    # 创建测试器
    server_url = "ws://localhost:7799"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
        
    tester = MultiCTPTester(server_url)
    
    # 连接服务器
    if not await tester.connect():
        return
    
    try:
        # 启动消息接收任务
        receive_task = asyncio.create_task(tester.receive_messages())
        
        # 等待连接建立
        await asyncio.sleep(3)
        
        # 执行测试
        print("🚀 开始多CTP连接测试")
        
        # 1. 测试大量订阅
        await tester.test_mass_subscription(test_instruments)
        
        # 2. 监控连接状态
        await tester.monitor_connections(60)
        
        # 3. 测试故障转移（可选）
        test_failover = input("\n是否测试故障转移? (y/N): ").strip().lower() == 'y'
        if test_failover:
            await tester.test_failover()
        
        print("\n📊 最终统计:")
        total_messages = sum(data['count'] for data in tester.received_data.values())
        active_instruments = len(tester.received_data)
        all_connections = set()
        
        for instrument, data in tester.received_data.items():
            all_connections.update(data['connections'])
            if data['count'] > 0:
                print(f"  {instrument}: {data['count']} 消息, 连接: {list(data['connections'])}")
        
        print(f"\n总计:")
        print(f"  活跃合约: {active_instruments}")
        print(f"  总消息数: {total_messages}")
        print(f"  使用连接: {len(all_connections)} - {list(all_connections)}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断测试")
    finally:
        if tester.websocket:
            await tester.websocket.close()
            
if __name__ == "__main__":
    # 检查帮助参数
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("🧪 QuantAxis 多CTP连接测试脚本")
        print("=" * 50)
        print("用法: python3 test_multi_ctp.py [WebSocket_URL]")
        print("默认URL: ws://127.0.0.1:7799")
        print("示例: python3 test_multi_ctp.py ws://localhost:7799")
        sys.exit(0)
    
    print("🧪 QuantAxis 多CTP连接测试脚本")
    print("=" * 50)
    asyncio.run(main())