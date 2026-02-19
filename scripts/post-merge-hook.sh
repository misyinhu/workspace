#!/bin/bash
# Git post-merge hook: 自动切换为远程环境配置

SETTINGS_FILE="config/settings.yaml"

cd "$(dirname "$0")/../.."

if [ -f "$SETTINGS_FILE" ]; then
    # 检查当前环境
    if grep -q "current: local" "$SETTINGS_FILE"; then
        echo "[deploy] 检测到本地配置，自动切换为远程环境..."
        sed -i.bak "s/current: local/current: remote/" "$SETTINGS_FILE"
        echo "[deploy] ✅ 已切换为 remote 环境"
        
        # 显示当前配置
        echo "[deploy] 当前配置:"
        grep "current:" "$SETTINGS_FILE"
    else
        echo "[deploy] 当前已是远程配置，无需修改"
    fi
else
    echo "[deploy] ⚠️ 未找到 settings.yaml"
fi
