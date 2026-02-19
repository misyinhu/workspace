#!/bin/bash
# =============================================================================
# 生产环境部署脚本
# 由 Git post-merge hook 自动调用，或手动执行
# =============================================================================

set -e

cd "$(dirname "$0")/.." || exit 1

# 只在远程环境执行
if [ ! -d "/Users/openclaw/trading_env" ]; then
    echo "[deploy] 非远程环境，跳过部署"
    exit 0
fi

echo "[deploy] ========== 开始部署 =========="

# 1. 检查并修正环境配置
echo "[deploy] Step 1: 检查环境配置..."
SETTINGS_FILE="config/settings.yaml"

if [ -f "$SETTINGS_FILE" ]; then
    if grep -q "current: local" "$SETTINGS_FILE"; then
        echo "[deploy] 检测到 local 配置，切换到 remote..."
        sed -i.bak "s/current: local/current: remote/" "$SETTINGS_FILE"
        echo "[deploy] ✅ 已切换到 remote 环境"
    else
        echo "[deploy] ✅ 环境配置正确 (remote)"
    fi
else
    echo "[deploy] ⚠️ 未找到 $SETTINGS_FILE"
fi

# 2. 重启 webhook 服务
echo "[deploy] Step 2: 重启 webhook 服务..."
launchctl stop com.openclaw.webhook 2>/dev/null || true
sleep 2
launchctl start com.openclaw.webhook
sleep 4

# 3. 验证服务状态
echo "[deploy] Step 3: 验证服务状态..."
if curl -s http://localhost:5002/health | grep -q '"status":"ok"'; then
    echo "[deploy] ✅ Webhook 服务运行正常"
else
    echo "[deploy] ❌ Webhook 服务启动失败"
    echo "[deploy] 查看日志: tail -f ~/logs/webhook.error.log"
    exit 1
fi

echo "[deploy] ========== 部署完成 =========="
