# QuantAxis Multi-CTP Gateway - Redis数据写入问题排查指南

## ❓ 问题描述
订阅合约后，Redis中没有市场数据更新。

## 🔍 问题排查步骤

### 1. 快速诊断
```bash
# 运行综合诊断脚本
./diagnose_issue.sh

# 运行Redis专门诊断
python3 debug_redis.py

# 检查特定Redis地址
python3 debug_redis.py 192.168.2.27:6379
```

### 2. 逐步检查清单

#### ✅ 检查服务状态
```bash
# 检查进程是否运行
ps aux | grep market_data_server

# 检查端口监听
netstat -tlnp | grep 7799

# 检查服务启动
./bin/market_data_server --multi-ctp
```

#### ✅ 检查Redis连接
```bash
# 测试Redis连接
redis-cli -h 192.168.2.27 -p 6379 ping

# 查看Redis数据
redis-cli -h 192.168.2.27 -p 6379 keys "market_data*"

# 检查特定合约数据
redis-cli -h 192.168.2.27 -p 6379 hgetall "market_data_hash:rb2501"
```

#### ✅ 检查CTP连接状态
```bash
# 检查CTP流文件
ls -la ctpflow/*/

# 查看连接文件
find ctpflow/ -name "*.con" -mmin -5
```

#### ✅ 检查日志文件
```bash
# 查看实时日志
tail -f logs/market_data_server.log

# 搜索错误信息
grep -i "error\|failed\|redis" logs/*.log

# 搜索市场数据相关日志
grep -i "market.*data\|OnRtnDepthMarketData" logs/*.log
```

## 🚨 常见问题及解决方案

### 问题1：Redis连接失败
**症状**: 日志显示"Failed to connect to Redis server"

**原因**:
- Redis服务未启动
- 网络连接问题
- 防火墙阻拦
- Redis配置错误

**解决方案**:
```bash
# 启动Redis服务
sudo systemctl start redis-server

# 检查Redis配置
sudo nano /etc/redis/redis.conf
# 确保bind配置允许外部连接

# 测试连接
redis-cli -h 192.168.2.27 -p 6379 ping
```

### 问题2：CTP连接失败
**症状**: ctpflow目录为空或无.con文件

**原因**:
- CTP服务器地址错误
- 用户名密码错误
- 网络连接问题
- 期货公司服务器维护

**解决方案**:
```bash
# 检查配置文件
cat config/multi_ctp_config.json

# 验证CTP服务器地址
telnet 180.168.146.187 10131

# 检查CTP流目录
ls -la ctpflow/guangfa_telecom/
```

### 问题3：订阅未成功
**症状**: 连接正常但无市场数据

**原因**:
- 合约代码错误
- 交易时间外
- CTP订阅限制
- 网络延迟

**解决方案**:
```bash
# 使用测试客户端验证
python3 test_multi_ctp.py ws://localhost:7799

# 订阅常见合约
# rb2501, cu2501, au2412 等
```

### 问题4：数据写入但Redis查询为空
**症状**: 日志显示写入成功但Redis查询无数据

**原因**:
- Redis数据库选择错误
- key命名不一致
- 数据过期策略
- 缓存层问题

**解决方案**:
```bash
# 检查所有数据库
for i in {0..15}; do
  echo "DB $i:"
  redis-cli -h 192.168.2.27 -p 6379 -n $i keys "market_data*" | wc -l
done

# 监控Redis写入
redis-cli -h 192.168.2.27 -p 6379 monitor
```

## 🔧 调试工具使用

### 诊断脚本
```bash
# 综合诊断
./diagnose_issue.sh

# Redis专项诊断  
python3 debug_redis.py

# 实时监控Redis数据写入
python3 debug_redis.py --monitor 60
```

### 测试客户端
```bash
# 多CTP测试客户端
python3 test_multi_ctp.py ws://localhost:7799

# 简单测试客户端
python3 simple_test_client.py

# 快速测试
python3 quick_test.py ws://localhost:7799
```

## 📊 数据流程确认

### 正常数据流程
1. **WebSocket客户端** → 发送订阅请求
2. **SubscriptionDispatcher** → 分配到最佳CTP连接  
3. **CTPConnection** → 向CTP服务器订阅
4. **OnRtnDepthMarketData** → 接收市场数据回调
5. **RedisClient** → 写入Redis数据库
6. **WebSocket广播** → 推送给订阅客户端

### 数据存储格式
```bash
# JSON格式存储
market_data:{instrument_id} = {完整JSON数据}

# Hash格式存储  
market_data_hash:{instrument_id} = {
  "last_price": "价格",
  "volume": "成交量", 
  "update_time": "更新时间",
  "trading_day": "交易日",
  "json_data": "完整JSON"
}
```

## 🎯 问题定位策略

### 1. 自上而下
- 检查WebSocket连接 → CTP连接 → Redis连接
- 确认订阅请求 → 数据接收 → 数据存储

### 2. 日志分析
- 启动日志：确认服务启动正常
- 连接日志：确认CTP和Redis连接成功  
- 订阅日志：确认合约订阅成功
- 数据日志：确认市场数据接收和存储

### 3. 实时监控
- Redis监控：`redis-cli monitor`
- 网络监控：`tcpdump -i any port 6379`
- 进程监控：`top -p $(pgrep market_data_server)`

## ✅ 验证修复

确认问题解决的标志：

1. **Redis中有数据**
   ```bash
   redis-cli -h 192.168.2.27 -p 6379 keys "market_data*" | wc -l
   # 应该 > 0
   ```

2. **数据实时更新**
   ```bash
   python3 debug_redis.py --monitor 30
   # 应该看到新增key和数据更新
   ```

3. **WebSocket推送正常**
   ```bash
   python3 test_multi_ctp.py ws://localhost:7799
   # 应该收到市场数据推送
   ```

4. **日志无错误**
   ```bash
   tail -f logs/market_data_server.log | grep -i error
   # 应该无Redis相关错误
   ```

**🎉 按此指南排查，问题应该能够快速定位和解决！**