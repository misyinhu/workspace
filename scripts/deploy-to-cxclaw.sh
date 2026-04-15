#!/bin/bash
set -e

# 目标 CXClaw 部署脚本
# 默认目标主机使用环境变量覆盖，便于在不同机器间切换
# 默认远程主机采用与 deploy-to-remote.sh 相同的远程路径配置

REMOTE_HOST="Apple@100.82.238.11"
REMOTE_DIR="${CXCLAW_DIR:-\$HOME}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMP_FILE="/tmp/trading_deploy_cxclaw.tar.gz"

echo "🌐 Packaging for CXClaw deployment..."
tar -czf "$TEMP_FILE" \
  --exclude='.git' \
  --exclude='AGENTS.md' \
  --exclude='.DS_Store' \
  --exclude='data/z120_status.json' \
  -C "$PROJECT_DIR" .

REMOTE_DIR="~/deploy_temp"

echo "📤 Uploading to remote..."
scp "$TEMP_FILE" "$REMOTE_HOST:$REMOTE_DIR/"

echo "🚀 Deploying on remote..."
ssh "$REMOTE_HOST" "mkdir -p /d/projects/trading && cd /d/projects/trading && tar -xzf $REMOTE_DIR/trading_deploy_cxclaw.tar.gz"

echo "✅ CXClaw deployment completed"
