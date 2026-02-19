#!/bin/bash
# =============================================================================
# 远程机器首次部署安装脚本
# 只需运行一次
# =============================================================================

set -e

echo "🚀 远程机器首次部署..."

# 1. 安装 Git hook
echo "[1/3] 安装 Git post-merge hook..."
if [ -f "scripts/post-merge" ]; then
    cp scripts/post-merge .git/hooks/post-merge
    chmod +x .git/hooks/post-merge
    echo "✅ Git hook 已安装"
else
    echo "⚠️ 未找到 scripts/post-merge"
    exit 1
fi

# 2. 运行部署脚本（首次）
echo "[2/3] 首次部署..."
./scripts/deploy.sh

# 3. 验证
echo "[3/3] 验证服务状态..."
if curl -s http://localhost:5002/health | grep -q '"status":"ok"'; then
    echo "✅ 服务运行正常"
else
    echo "⚠️ 服务异常，请检查日志: tail -f ~/logs/webhook.error.log"
fi

echo ""
echo "🎉 首次部署完成！"
echo ""
echo "后续部署只需执行: git pull"
echo "hook 会自动触发 scripts/deploy.sh"
