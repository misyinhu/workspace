#!/bin/bash
# =============================================================================
# 部署到远程服务器
# 本地运行
# =============================================================================

set -e

REMOTE_HOST="openclaw@100.102.240.31"
REMOTE_DIR="/tmp"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMP_FILE="/tmp/trading_deploy.tar.gz"

echo "📦 打包项目文件..."
tar -czf "$TEMP_FILE" \
  --exclude='.git' \
  --exclude='config/settings.yaml' \
  --exclude='AGENTS.md' \
  --exclude='.DS_Store' \
  --exclude='data/z120_status.json' \
  -C "$PROJECT_DIR" .

echo "📤 传输到远程服务器..."
scp "$TEMP_FILE" "$REMOTE_HOST:$REMOTE_DIR/"

echo "🚀 远程部署..."
ssh "$REMOTE_HOST" "cd ~/.openclaw/workspace/trading && tar -xzf $REMOTE_DIR/trading_deploy.tar.gz && ./scripts/deploy.sh"

echo "✅ 部署完成"
