#!/bin/bash

# QuantAxis Multi-CTP Gateway 问题诊断脚本
# 检查订阅后数据未写入Redis的原因

echo "🔍 QuantAxis Multi-CTP Gateway 问题诊断"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 检查服务是否运行
echo -e "\n${YELLOW}1. 检查qactpmdgateway服务状态${NC}"
if pgrep -f "market_data_server" > /dev/null; then
    echo -e "${GREEN}✅ qactpmdgateway服务正在运行${NC}"
    PID=$(pgrep -f "market_data_server")
    echo -e "   进程ID: $PID"
else
    echo -e "${RED}❌ qactpmdgateway服务未运行${NC}"
    echo -e "${YELLOW}   请先启动服务: ./bin/market_data_server --multi-ctp${NC}"
fi

# 2. 检查端口监听
echo -e "\n${YELLOW}2. 检查WebSocket端口监听${NC}"
if netstat -tlnp 2>/dev/null | grep ":7799" > /dev/null; then
    echo -e "${GREEN}✅ WebSocket端口7799正在监听${NC}"
    netstat -tlnp 2>/dev/null | grep ":7799"
else
    echo -e "${RED}❌ WebSocket端口7799未监听${NC}"
fi

# 3. 检查Redis连接
echo -e "\n${YELLOW}3. 检查Redis连接${NC}"
REDIS_HOST="192.168.2.27"
REDIS_PORT="6379"

if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli -h $REDIS_HOST -p $REDIS_PORT ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}✅ Redis连接正常 ($REDIS_HOST:$REDIS_PORT)${NC}"
        
        # 检查Redis中的数据
        MARKET_DATA_COUNT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT --scan --pattern "market_data:*" | wc -l 2>/dev/null || echo "0")
        MARKET_HASH_COUNT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT --scan --pattern "market_data_hash:*" | wc -l 2>/dev/null || echo "0")
        
        echo -e "   市场数据key数量: $MARKET_DATA_COUNT"
        echo -e "   市场数据hash数量: $MARKET_HASH_COUNT"
        
        if [ "$MARKET_DATA_COUNT" -gt 0 ] || [ "$MARKET_HASH_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✅ Redis中有市场数据${NC}"
        else
            echo -e "${YELLOW}⚠️  Redis中暂无市场数据${NC}"
        fi
    else
        echo -e "${RED}❌ Redis连接失败 ($REDIS_HOST:$REDIS_PORT)${NC}"
        echo -e "${YELLOW}   请检查Redis服务是否启动${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  redis-cli未安装，无法检查Redis连接${NC}"
    echo -e "${YELLOW}   安装命令: sudo apt-get install redis-tools${NC}"
fi

# 4. 检查日志文件
echo -e "\n${YELLOW}4. 检查日志文件${NC}"
LOG_DIR="logs"
if [ -d "$LOG_DIR" ]; then
    LOG_FILES=$(find $LOG_DIR -name "*.log" -type f 2>/dev/null | head -5)
    if [ -n "$LOG_FILES" ]; then
        echo -e "${GREEN}✅ 找到日志文件:${NC}"
        echo "$LOG_FILES" | while read -r logfile; do
            echo "   - $logfile"
            # 检查最近的错误
            if grep -q "ERROR\|Failed\|Error" "$logfile" 2>/dev/null; then
                echo -e "${RED}     ⚠️  发现错误信息${NC}"
                echo "     最近错误:"
                tail -n 5 "$logfile" | grep -i "error\|failed" | head -2 | sed 's/^/       /'
            fi
        done
        
        # 检查Redis相关日志
        echo -e "\n${BLUE}   检查Redis相关日志:${NC}"
        find $LOG_DIR -name "*.log" -type f -exec grep -l "Redis\|redis" {} \; 2>/dev/null | while read -r logfile; do
            echo "   Redis相关日志 ($logfile):"
            grep -i "redis" "$logfile" 2>/dev/null | tail -3 | sed 's/^/     /'
        done
    else
        echo -e "${YELLOW}⚠️  未找到日志文件${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  日志目录不存在: $LOG_DIR${NC}"
fi

# 5. 检查CTP连接文件
echo -e "\n${YELLOW}5. 检查CTP连接状态${NC}"
CTP_FLOW_DIR="ctpflow"
if [ -d "$CTP_FLOW_DIR" ]; then
    CONNECTION_DIRS=$(find $CTP_FLOW_DIR -maxdepth 1 -type d -name "*" | grep -v "^$CTP_FLOW_DIR$" | wc -l)
    echo -e "   CTP连接目录数量: $CONNECTION_DIRS"
    
    if [ "$CONNECTION_DIRS" -gt 0 ]; then
        echo -e "${GREEN}✅ 找到CTP连接目录${NC}"
        find $CTP_FLOW_DIR -maxdepth 1 -type d | head -5 | while read -r dir; do
            if [ "$dir" != "$CTP_FLOW_DIR" ]; then
                echo "   - $dir"
                # 检查连接文件
                CON_FILES=$(find "$dir" -name "*.con" -type f 2>/dev/null | wc -l)
                if [ "$CON_FILES" -gt 0 ]; then
                    echo -e "${GREEN}     ✅ 有连接文件 ($CON_FILES个)${NC}"
                else
                    echo -e "${YELLOW}     ⚠️  无连接文件${NC}"
                fi
            fi
        done
    else
        echo -e "${YELLOW}⚠️  未找到CTP连接目录${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  CTP流目录不存在: $CTP_FLOW_DIR${NC}"
fi

# 6. 检查配置文件
echo -e "\n${YELLOW}6. 检查配置文件${NC}"
CONFIG_FILE="config/multi_ctp_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✅ 配置文件存在: $CONFIG_FILE${NC}"
    
    # 检查配置中的连接数量
    if command -v jq >/dev/null 2>&1; then
        CONNECTION_COUNT=$(jq '.connections | length' "$CONFIG_FILE" 2>/dev/null || echo "unknown")
        REDIS_HOST_CONFIG=$(jq -r '.redis_host // "unknown"' "$CONFIG_FILE" 2>/dev/null)
        REDIS_PORT_CONFIG=$(jq -r '.redis_port // "unknown"' "$CONFIG_FILE" 2>/dev/null)
        
        echo "   配置的连接数量: $CONNECTION_COUNT"
        echo "   配置的Redis地址: $REDIS_HOST_CONFIG:$REDIS_PORT_CONFIG"
    else
        echo -e "${YELLOW}   (jq未安装，无法解析JSON配置)${NC}"
    fi
else
    echo -e "${RED}❌ 配置文件不存在: $CONFIG_FILE${NC}"
fi

# 7. 生成问题诊断报告
echo -e "\n${BLUE}📋 问题诊断总结${NC}"
echo "================================"

# 检查常见问题
echo -e "\n${YELLOW}可能的问题原因:${NC}"

# 服务未运行
if ! pgrep -f "market_data_server" > /dev/null; then
    echo -e "${RED}❌ 1. qactpmdgateway服务未启动${NC}"
    echo -e "   解决方案: ./bin/market_data_server --multi-ctp"
fi

# Redis连接问题
if command -v redis-cli >/dev/null 2>&1; then
    if ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${RED}❌ 2. Redis连接失败${NC}"
        echo -e "   解决方案: 检查Redis服务是否启动，网络连接是否正常"
    fi
fi

# 端口未监听
if ! netstat -tlnp 2>/dev/null | grep ":7799" > /dev/null; then
    echo -e "${RED}❌ 3. WebSocket端口未监听${NC}"
    echo -e "   解决方案: 检查服务启动是否成功，查看日志"
fi

echo -e "\n${BLUE}🔧 建议的调试步骤:${NC}"
echo "1. 运行Redis诊断: python3 debug_redis.py"
echo "2. 检查服务日志: tail -f logs/market_data_server.log"
echo "3. 使用测试客户端: python3 test_multi_ctp.py"
echo "4. 检查CTP连接: ls -la ctpflow/*/"

echo -e "\n${GREEN}诊断完成！${NC}"