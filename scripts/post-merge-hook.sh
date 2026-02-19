#!/bin/bash
# Git post-merge hook: 自动切换为远程环境配置
# 仅在 settings.yaml 被修改时执行

SETTINGS_FILE="config/settings.yaml"

cd "$(dirname "$0")/../.."

# 检查 settings.yaml 是否在本次 merge 中被修改
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep -q "$SETTINGS_FILE"; then
    echo "[deploy] 检测到 $SETTINGS_FILE 已更新"
    
    if [ -f "$SETTINGS_FILE" ]; then
        # 检查当前环境
        if grep -q "current: local" "$SETTINGS_FILE"; then
            echo "[deploy] 自动切换为远程环境..."
            sed -i.bak "s/current: local/current: remote/" "$SETTINGS_FILE"
            echo "[deploy] ✅ 已切换为 remote 环境"
            
            # 显示当前配置
            echo "[deploy] 当前配置:"
            grep "current:" "$SETTINGS_FILE"
        else
            echo "[deploy] 当前已是远程配置，无需修改"
        fi
    else
        echo "[deploy] ⚠️ 未找到 $SETTINGS_FILE"
    fi
else
    # settings.yaml 未被修改，静默退出
    exit 0
fi
