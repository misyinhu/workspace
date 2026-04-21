#!/bin/bash
set -e

# 部署脚本 — 将本地代码同步到远程 Windows 交易服务器
# 用法: ./scripts/deploy-to-cxclaw.sh [远程主机]
# 环境变量:
#   REMOTE_HOST  - 远程主机 (默认 Apple@100.82.238.11)
#   REMOTE_DIR   - 远程项目目录 (默认 D:/projects/trading)

REMOTE_HOST="${REMOTE_HOST:-Apple@100.82.238.11}"
REMOTE_DIR="${REMOTE_DIR:-D:/projects/trading}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMP_BUNDLE="/tmp/trading.bundle"

echo "📦 Creating git bundle..."
cd "$PROJECT_DIR"
git bundle create "$TEMP_BUNDLE" --all

echo "📤 Uploading bundle to remote..."
scp "$TEMP_BUNDLE" "$REMOTE_HOST:C:/Users/Apple/AppData/Local/Temp/trading.bundle"

echo "🔄 Syncing on remote (stash → pull → pop)..."
ssh "$REMOTE_HOST" bash -c "'
  cd $REMOTE_DIR || exit 1
  # 暂存远程未提交的修改
  git stash --quiet 2>/dev/null
  # 拉取最新代码
  git pull /c/Users/Apple/AppData/Local/Temp/trading.bundle main
  # 恢复暂存的修改
  git stash pop --quiet 2>/dev/null
  echo \"✅ Remote at \$(git log --oneline -1)\"
'"

echo "🧹 Cleaning up..."
rm -f "$TEMP_BUNDLE"

echo "✅ Deployment completed"
