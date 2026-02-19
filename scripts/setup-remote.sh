#!/bin/bash
# =============================================================================
# 远程机器初始化脚本
# 在首次部署或重新克隆后运行
# =============================================================================

set -e

echo "🚀 远程机器初始化..."

# 1. 安装 Git hook
echo "[1/3] 安装 Git post-merge hook..."
if [ -f "scripts/post-merge-hook.sh" ]; then
    cp scripts/post-merge-hook.sh .git/hooks/post-merge
    chmod +x .git/hooks/post-merge
    echo "✅ Git hook 已安装"
else
    echo "⚠️ 未找到 scripts/post-merge-hook.sh"
fi

# 2. 立即执行 hook 切换环境
echo "[2/3] 切换为远程环境配置..."
if [ -f ".git/hooks/post-merge" ]; then
    .git/hooks/post-merge
else
    echo "⚠️ Hook 未安装，手动切换..."
    sed -i.bak "s/current: local/current: remote/" config/settings.yaml 2>/dev/null || true
fi

# 3. 验证配置
echo "[3/3] 验证配置..."
if grep -q "current: remote" config/settings.yaml; then
    echo "✅ 环境配置正确: remote"
else
    echo "⚠️ 请检查 config/settings.yaml"
    grep "current:" config/settings.yaml
fi

echo ""
echo "🎉 初始化完成！"
echo ""
echo "后续部署只需执行: git pull"
echo "hook 会自动切换 current: local → remote"
