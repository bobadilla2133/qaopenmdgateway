#!/bin/bash
# 安装Python测试客户端依赖

echo "🚀 安装Python WebSocket测试客户端依赖..."

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3"
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "📦 安装pip3..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

echo "📦 安装WebSocket客户端库..."

# 安装异步WebSocket库（推荐）
echo "安装 websockets (异步版本)..."
pip3 install websockets

# 安装同步WebSocket库（备用）
echo "安装 websocket-client (同步版本)..."
pip3 install websocket-client

echo "✅ Python依赖安装完成！"

echo ""
echo "🎯 使用方法:"
echo "1. 异步版本（推荐）:"
echo "   python3 test_client.py [服务器地址] [合约列表]"
echo "   例: python3 test_client.py ws://localhost:7799 rb2601,i2501"
echo ""
echo "2. 同步版本（简化）:"
echo "   python3 simple_test_client.py [服务器地址]"
echo "   例: python3 simple_test_client.py ws://localhost:7799"
echo ""
echo "🔧 确保你的市场数据服务器正在运行:"
echo "   ./bin/market_data_server --front-addr tcp://182.254.243.31:30011 --broker-id 9999"