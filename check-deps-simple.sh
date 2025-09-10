#!/bin/bash
echo "🔍 快速依赖检查"

# 检查RapidJSON
if [ -f "include/rapidjson/rapidjson.h" ]; then
    echo "✅ RapidJSON: 已捆绑"
else
    echo "❌ RapidJSON: 缺失"
fi

# 检查open-trade-common
if [ -f "include/open-trade-common/types.h" ]; then
    echo "✅ open-trade-common: 已捆绑"
else
    echo "❌ open-trade-common: 缺失"
fi

# 检查CTP库
if [ -f "libs/thostmduserapi_se.so" ]; then
    echo "✅ CTP库: 已捆绑"
else
    echo "❌ CTP库: 缺失"
fi