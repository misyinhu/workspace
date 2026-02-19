#!/bin/bash
# Git post-merge hook: 部署后自动初始化

cd "$(dirname "$0")/../.."

echo "[deploy] 运行初始化脚本..."

# 运行 init.sh（会自动检测并修正环境配置）
if [ -x "./init.sh" ]; then
    ./init.sh
else
    echo "[deploy] ⚠️ init.sh 不存在或不可执行"
fi

