#!/bin/bash
# QuantAxis Multi-CTP Gateway Docker构建脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="qactpmdgateway"
IMAGE_NAME="quantaxis/${PROJECT_NAME}"
VERSION="2.0.0"

echo -e "${BLUE}🚀 QuantAxis Multi-CTP Market Data Gateway${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查Docker环境
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装，请先安装Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose未安装，请先安装Docker Compose${NC}"
    exit 1
fi

# 清理旧的构建文件
echo -e "${YELLOW}🧹 清理旧的构建文件...${NC}"
make clean || true
rm -rf ctpflow/ logs/ backup/ || true

# 确保必要的目录存在
echo -e "${YELLOW}📁 创建必要的目录结构...${NC}"
mkdir -p {config,logs,ctpflow,backup}

# 构建Docker镜像
echo -e "${YELLOW}🔨 构建Docker镜像...${NC}"
docker build \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
    -t ${IMAGE_NAME}:${VERSION} \
    -t ${IMAGE_NAME}:latest \
    .

# 检查构建结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker镜像构建成功！${NC}"
    echo -e "${GREEN}   镜像标签: ${IMAGE_NAME}:${VERSION}${NC}"
    echo -e "${GREEN}   镜像标签: ${IMAGE_NAME}:latest${NC}"
else
    echo -e "${RED}❌ Docker镜像构建失败！${NC}"
    exit 1
fi

# 显示镜像信息
echo -e "${BLUE}📊 镜像信息：${NC}"
docker images ${IMAGE_NAME} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# 提供使用说明
echo
echo -e "${GREEN}🎉 构建完成！使用方法：${NC}"
echo
echo -e "${YELLOW}单独运行容器：${NC}"
echo "  docker run -d \\"
echo "    --name qactpmd-gateway \\"
echo "    -p 7799:7799 \\"
echo "    -v \$(pwd)/config:/opt/quantaxis/qactpmdgateway/config:ro \\"
echo "    -v \$(pwd)/logs:/opt/quantaxis/qactpmdgateway/logs \\"
echo "    ${IMAGE_NAME}:${VERSION}"
echo
echo -e "${YELLOW}使用Docker Compose：${NC}"
echo "  docker-compose up -d"
echo
echo -e "${YELLOW}包含监控界面：${NC}"
echo "  docker-compose --profile monitoring up -d"
echo
echo -e "${YELLOW}查看日志：${NC}"
echo "  docker-compose logs -f qactpmdgateway"
echo
echo -e "${YELLOW}停止服务：${NC}"
echo "  docker-compose down"