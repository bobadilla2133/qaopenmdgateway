# 多CTP连接系统使用说明

## 🚀 快速开始

### 1. 编译项目

```bash
cd qactpmdgateway
make all
```

### 2. 运行模式

#### 单CTP模式（兼容性模式）
```bash
./bin/market_data_server --front-addr tcp://182.254.243.31:30011 --broker-id 9999 --port 7799
```

#### 多CTP模式（推荐）

使用默认配置（SimNow环境）：
```bash
./bin/market_data_server --multi-ctp
```

使用自定义配置文件：
```bash
./bin/market_data_server --config config/multi_ctp_config.json
```

指定负载均衡策略：
```bash
./bin/market_data_server --multi-ctp --strategy connection_quality
```

### 3. 查看连接状态

```bash
./bin/market_data_server --multi-ctp --status
```

## 📋 配置文件格式

配置文件使用JSON格式，示例：

```json
{
  "broker_id": "9999",
  "websocket_port": 7799,
  "redis_host": "192.168.2.27",
  "redis_port": 6379,
  "load_balance_strategy": "connection_quality",
  "health_check_interval": 30,
  "maintenance_interval": 60,
  "max_retry_count": 3,
  "auto_failover": true,
  "connections": [
    {
      "connection_id": "simnow_telecom",
      "front_addr": "tcp://180.168.146.187:10210",
      "broker_id": "9999",
      "max_subscriptions": 500,
      "priority": 1,
      "enabled": true
    }
  ]
}
```

### 配置参数说明

#### 全局配置
- `broker_id`: CTP Broker ID
- `websocket_port`: WebSocket服务端口
- `redis_host`: Redis服务器地址
- `redis_port`: Redis服务器端口
- `load_balance_strategy`: 负载均衡策略
- `health_check_interval`: 健康检查间隔（秒）
- `maintenance_interval`: 维护任务间隔（秒）
- `max_retry_count`: 最大重试次数
- `auto_failover`: 是否启用自动故障转移

#### 连接配置
- `connection_id`: 连接唯一标识
- `front_addr`: CTP前置机地址
- `broker_id`: 该连接的Broker ID
- `max_subscriptions`: 最大订阅数
- `priority`: 连接优先级（1-10，数字越小优先级越高）
- `enabled`: 是否启用该连接

## ⚖️ 负载均衡策略

### 1. Connection Quality (推荐)
```bash
--strategy connection_quality
```
根据连接质量评分选择最佳连接，综合考虑：
- 连接稳定性
- 错误率
- 订阅负载
- 网络延迟

### 2. Least Connections
```bash
--strategy least_connections
```
选择当前订阅数最少的连接

### 3. Round Robin
```bash
--strategy round_robin
```
轮询方式分配连接

### 4. Hash Based
```bash
--strategy hash_based
```
基于合约ID哈希值选择连接，确保相同合约总是分配到相同连接

## 🧪 测试功能

### 运行多CTP测试脚本

```bash
# 安装Python依赖
pip3 install websockets

# 启动服务器（多CTP模式）
./bin/market_data_server --multi-ctp &

# 运行测试脚本
python3 test_multi_ctp.py

# 或指定服务器地址
python3 test_multi_ctp.py ws://localhost:7799
```

### 测试项目
- ✅ 大量合约订阅（几千个合约）
- ✅ 负载均衡验证
- ✅ 连接状态监控
- ✅ 故障转移测试
- ✅ 性能统计

## 🔧 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  MarketDataServer (主控制器)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│              SubscriptionDispatcher (全局订阅分发器)            │
│  - 全局订阅管理                                                │
│  - 负载均衡算法                                                │
│  - 故障转移处理                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                CTPConnectionManager                              │
│                   (多连接管理器)                                │
└─────────┬───────────────┬───────────────┬─────────────────────┘
          │               │               │
┌─────────▼─────┐ ┌───────▼─────┐ ┌───────▼─────┐ 
│ CTPConnection1│ │CTPConnection2│ │CTPConnection3│ ... 
│ Front-A       │ │ Front-B     │ │ Front-C     │
└───────────────┘ └─────────────┘ └─────────────┘
```

## 🎯 核心特性

### 1. 智能订阅分发
- 全局订阅去重
- 智能负载均衡
- 自动连接选择

### 2. 故障转移
- 连接健康监控
- 自动故障检测
- 订阅迁移

### 3. 性能优化
- 并发连接管理
- 异步消息处理
- Redis数据缓存

### 4. 监控统计
- 实时连接状态
- 订阅分布统计
- 性能指标监控

## 📊 WebSocket API

### 订阅合约
```json
{
  "action": "subscribe",
  "instruments": ["rb2501", "i2501", "au2412"]
}
```

### 取消订阅
```json
{
  "action": "unsubscribe", 
  "instruments": ["rb2501"]
}
```

### 查询合约列表
```json
{
  "action": "list_instruments"
}
```

### 搜索合约
```json
{
  "action": "search_instruments",
  "pattern": "rb"
}
```

## ❓ 常见问题

### Q: 如何确认多CTP模式正在工作？
A: 启动服务器时会显示：
```
Multi-CTP Mode Configuration:
  Connections: 3 configured
  [simnow_telecom] tcp://180.168.146.187:10210
  [simnow_unicom] tcp://180.168.146.187:10211
  [simnow_mobile] tcp://218.202.237.33:10212
```

### Q: 如何监控连接质量？
A: 使用 `--status` 参数查看：
```bash
./bin/market_data_server --multi-ctp --status
```

### Q: 配置文件在哪里？
A: 
- 示例配置：`config/multi_ctp_config.json`
- 生产配置：`config/production_config.json`

### Q: 如何调整最大订阅数？
A: 修改配置文件中的 `max_subscriptions` 参数

### Q: 如何禁用某个连接？
A: 将配置文件中的 `enabled` 设为 `false`

## 🔒 生产环境部署

### 1. 配置优化
```json
{
  "max_subscriptions": 1000,
  "health_check_interval": 15,
  "maintenance_interval": 30,
  "auto_failover": true
}
```

### 2. 系统优化
```bash
# 增加文件描述符限制
ulimit -n 65536

# 优化网络参数
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
sysctl -p
```

### 3. 监控脚本
```bash
#!/bin/bash
# 监控服务状态
while true; do
    ./bin/market_data_server --status --config config/production_config.json
    sleep 60
done
```

## 📈 性能指标

### 典型性能数据
- 支持并发订阅: 5000+ 合约
- 消息处理延迟: <1ms
- 内存使用: ~100MB (无订阅) - 500MB (满载)
- CPU使用: 2-10% (4核服务器)

### 扩展建议
- 单机推荐: 3-5个CTP连接
- 每连接建议: 500-1000个订阅
- 总订阅建议: <5000个合约

---

更多问题请查看项目README或提交Issue。