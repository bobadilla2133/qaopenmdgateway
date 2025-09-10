#!/bin/bash
# QuantAxis Multi-CTP Gateway 依赖检查脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 QuantAxis Multi-CTP Gateway 依赖检查${NC}"
echo -e "${BLUE}=================================${NC}"

# 检查编译器
echo -e "${YELLOW}检查编译器...${NC}"
if command -v g++ &> /dev/null; then
    GCC_VERSION=$(g++ --version | head -n1)
    echo -e "${GREEN}✅ GCC: $GCC_VERSION${NC}"
else
    echo -e "${RED}❌ GCC未安装${NC}"
    exit 1
fi

# 检查C++17支持
echo -e "${YELLOW}检查C++17支持...${NC}"
echo 'int main() { return 0; }' | g++ -std=c++17 -x c++ -o /tmp/cpp17test - 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ C++17支持正常${NC}"
    rm -f /tmp/cpp17test
else
    echo -e "${RED}❌ C++17支持异常${NC}"
    exit 1
fi

# 检查Boost库
echo -e "${YELLOW}检查Boost库...${NC}"
if pkg-config --exists --atleast-version=1.65 boost; then
    BOOST_VERSION=$(pkg-config --modversion boost 2>/dev/null || echo "未知版本")
    echo -e "${GREEN}✅ Boost: $BOOST_VERSION${NC}"
elif find /usr/include -name "boost" -type d 2>/dev/null | grep -q boost; then
    echo -e "${GREEN}✅ Boost: 已安装(版本未知)${NC}"
else
    echo -e "${RED}❌ Boost未安装${NC}"
    echo -e "${YELLOW}安装命令: sudo apt-get install libboost-all-dev${NC}"
fi

# 检查RapidJSON
echo -e "${YELLOW}检查RapidJSON...${NC}"
if find /usr/include -name "rapidjson" -type d 2>/dev/null | grep -q rapidjson; then
    echo -e "${GREEN}✅ RapidJSON: 已安装${NC}"
else
    echo -e "${RED}❌ RapidJSON未安装${NC}"
    echo -e "${YELLOW}安装命令: sudo apt-get install rapidjson-dev${NC}"
fi

# 检查SSL库
echo -e "${YELLOW}检查SSL库...${NC}"
if pkg-config --exists openssl; then
    SSL_VERSION=$(pkg-config --modversion openssl)
    echo -e "${GREEN}✅ OpenSSL: $SSL_VERSION${NC}"
else
    echo -e "${RED}❌ OpenSSL未安装${NC}"
    echo -e "${YELLOW}安装命令: sudo apt-get install libssl-dev${NC}"
fi

# 检查cURL库
echo -e "${YELLOW}检查cURL库...${NC}"
if pkg-config --exists libcurl; then
    CURL_VERSION=$(pkg-config --modversion libcurl)
    echo -e "${GREEN}✅ cURL: $CURL_VERSION${NC}"
else
    echo -e "${RED}❌ cURL开发库未安装${NC}"
    echo -e "${YELLOW}安装命令: sudo apt-get install libcurl4-openssl-dev${NC}"
fi

# 检查Redis库
echo -e "${YELLOW}检查Redis客户端库...${NC}"
if pkg-config --exists hiredis; then
    HIREDIS_VERSION=$(pkg-config --modversion hiredis)
    echo -e "${GREEN}✅ HiRedis: $HIREDIS_VERSION${NC}"
else
    echo -e "${RED}❌ HiRedis未安装${NC}"
    echo -e "${YELLOW}安装命令: sudo apt-get install libhiredis-dev${NC}"
fi

# 检查CTP库文件
echo -e "${YELLOW}检查CTP库文件...${NC}"
if [ -f "libs/thostmduserapi_se.so" ] && [ -f "libs/thosttraderapi_se.so" ]; then
    echo -e "${GREEN}✅ CTP库文件: 存在${NC}"
else
    echo -e "${RED}❌ CTP库文件缺失${NC}"
    echo -e "${YELLOW}请确保libs/目录包含CTP库文件${NC}"
fi

# 检查头文件
echo -e "${YELLOW}检查项目头文件...${NC}"
if [ -f "include/open-trade-common/types.h" ]; then
    echo -e "${GREEN}✅ 项目头文件: 存在${NC}"
else
    echo -e "${RED}❌ 项目头文件缺失${NC}"
    echo -e "${YELLOW}请确保include/目录包含必要头文件${NC}"
fi

# 检查目录结构
echo -e "${YELLOW}检查目录结构...${NC}"
REQUIRED_DIRS=("src" "include" "libs" "config" "obj" "bin")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ 目录 $dir: 存在${NC}"
    else
        echo -e "${YELLOW}⚠️  目录 $dir: 不存在，将创建${NC}"
        mkdir -p "$dir"
    fi
done

# 检查Make工具
echo -e "${YELLOW}检查Make工具...${NC}"
if command -v make &> /dev/null; then
    MAKE_VERSION=$(make --version | head -n1)
    echo -e "${GREEN}✅ Make: $MAKE_VERSION${NC}"
else
    echo -e "${RED}❌ Make未安装${NC}"
    echo -e "${YELLOW}安装命令: sudo apt-get install make${NC}"
fi

echo
echo -e "${BLUE}📋 依赖检查完成${NC}"
echo

# 提供安装建议
echo -e "${BLUE}💡 完整安装命令 (Ubuntu/Debian):${NC}"
echo "sudo apt-get update"
echo "sudo apt-get install -y \\"
echo "    build-essential \\"
echo "    libboost-all-dev \\"
echo "    libssl-dev \\"
echo "    libcurl4-openssl-dev \\"
echo "    libhiredis-dev \\"
echo "    rapidjson-dev"
echo

echo -e "${BLUE}🔨 编译命令:${NC}"
echo "make clean && make all"
echo

echo -e "${BLUE}🚀 启动命令:${NC}"
echo "./bin/market_data_server --multi-ctp"