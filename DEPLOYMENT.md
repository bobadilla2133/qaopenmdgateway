# QuantAxis Multi-CTP Market Data Gateway 部署指南

## 📦 独立项目特性

此项目已重构为完全独立的可编译项目，包含：

- ✅ **完整的依赖库** - 所有.so文件和头文件已内置
- ✅ **独立编译系统** - 无需外部依赖项目
- ✅ **Docker支持** - 基于Ubuntu 20.04的容器化部署
- ✅ **90期货公司** - 支持全国主要期货公司连接
- ✅ **25000+订阅** - 海量合约并发处理能力

## 🏗️ 项目结构

```
qactpmdgateway/
├── src/                          # 源代码
├── include/                      # 头文件
│   └── open-trade-common/       # 项目依赖头文件
├── libs/                        # CTP库文件
├── config/                      # 配置文件
├── obj/                         # 编译中间文件
├── bin/                         # 可执行文件
├── ctpflow/                     # CTP流文件目录
├── logs/                        # 日志文件
├── backup/                      # 备份文件
├── Dockerfile                   # Docker构建文件
├── docker-compose.yml           # Docker Compose配置
├── docker-build.sh              # Docker构建脚本
└── Makefile                     # 独立编译配置
```

## 🔧 本地编译部署

### 系统要求
- **操作系统**: Ubuntu 20.04+ / CentOS 7+
- **编译器**: GCC 7.0+ (支持C++17)
- **内存**: 至少1GB可用内存
- **磁盘**: 至少2GB可用空间

### 依赖安装
```bash
# Ubuntu/Debian系统
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    libboost-all-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    libhiredis-dev \
    rapidjson-dev

# CentOS/RHEL系统
sudo yum install -y \
    gcc-c++ \
    cmake \
    boost-devel \
    openssl-devel \
    libcurl-devel \
    hiredis-devel \
    rapidjson-devel
```

### 编译步骤
```bash
# 1. 进入项目目录
cd qactpmdgateway

# 2. 编译项目
make clean
make all

# 3. 验证编译结果
./bin/market_data_server --help

# 4. 启动服务(默认多CTP模式)
./bin/market_data_server --multi-ctp
```

## 🐳 Docker部署

### 快速开始
```bash
# 1. 构建镜像
chmod +x docker-build.sh
./docker-build.sh

# 2. 启动服务
docker-compose up -d

# 3. 查看状态
docker-compose ps
docker-compose logs -f qactpmdgateway

# 4. 停止服务
docker-compose down
```

### Docker单独运行
```bash
# 运行容器
docker run -d \
  --name qactpmd-gateway \
  -p 7799:7799 \
  -v $(pwd)/config:/opt/quantaxis/qactpmdgateway/config:ro \
  -v $(pwd)/logs:/opt/quantaxis/qactpmdgateway/logs \
  -v $(pwd)/ctpflow:/opt/quantaxis/qactpmdgateway/ctpflow \
  quantaxis/qactpmdgateway:latest

# 查看日志
docker logs -f qactpmd-gateway

# 进入容器
docker exec -it qactpmd-gateway bash
```

### 包含监控的完整部署
```bash
# 启动包含Portainer管理界面
docker-compose --profile monitoring up -d

# 访问管理界面
# Portainer: http://localhost:9000
# WebSocket: ws://localhost:7799
```

## ⚙️ 配置说明

### 基础配置
```bash
# 使用默认SimNow配置
./bin/market_data_server --multi-ctp

# 使用自定义配置文件
./bin/market_data_server --config config/multi_ctp_config.json

# 指定负载均衡策略
./bin/market_data_server --multi-ctp --strategy round_robin
```

### 环境变量 (Docker)
```bash
# docker-compose.yml 或运行时设置
TZ=Asia/Shanghai              # 时区设置
REDIS_HOST=redis             # Redis主机
REDIS_PORT=6379              # Redis端口
LOG_LEVEL=INFO               # 日志级别
```

## 🔍 验证部署

### 服务状态检查
```bash
# 检查进程
ps aux | grep market_data_server

# 检查端口
netstat -tlnp | grep 7799

# 检查WebSocket连接
curl --include \
     --no-buffer \
     --header "Connection: Upgrade" \
     --header "Upgrade: websocket" \
     --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     --header "Sec-WebSocket-Version: 13" \
     http://localhost:7799/
```

### 功能测试
```bash
# 使用Python测试客户端
python3 test_multi_ctp.py ws://localhost:7799

# 测试订阅功能
python3 quick_test.py ws://localhost:7799
```

## 📊 监控和维护

### 系统监控
```bash
# 连接状态
ls -la ctpflow/ | wc -l

# 活跃连接
find ctpflow/ -name "*.con" -mmin -5 | wc -l

# 资源使用
top -p $(pgrep market_data_server)
```

### 日志管理
```bash
# 查看实时日志
tail -f logs/market_data_server.log

# 日志轮转(建议添加到crontab)
find logs/ -name "*.log" -mtime +7 -delete
```

### 备份策略
```bash
# 配置文件备份
cp -r config/ backup/config_$(date +%Y%m%d)/

# CTP Flow文件备份
tar -czf backup/ctpflow_$(date +%Y%m%d_%H%M).tar.gz ctpflow/
```

## 🚀 生产环境优化

### 性能调优
```bash
# 系统参数优化
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 网络参数优化
echo 'net.core.rmem_max = 268435456' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 268435456' >> /etc/sysctl.conf
sysctl -p
```

### 服务管理
```bash
# 创建systemd服务
sudo cp scripts/qactpmd.service /etc/systemd/system/
sudo systemctl enable qactpmd
sudo systemctl start qactpmd
```

## 🆘 故障排除

### 常见问题

**编译错误**:
```bash
# 检查依赖
make check-deps

# 清理重编译
make clean && make all
```

**连接问题**:
```bash
# 检查CTP流文件
ls -la ctpflow/*/

# 查看错误日志
grep ERROR logs/market_data_server.log
```

**Docker问题**:
```bash
# 重新构建镜像
docker-compose down
docker system prune -f
./docker-build.sh
```

## 📞 技术支持

- **GitHub**: https://github.com/quantaxis/qactpmdgateway
- **文档**: README.md
- **邮箱**: support@quantaxis.io