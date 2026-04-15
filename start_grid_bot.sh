#!/bin/bash
cd ~/.openclaw/workspace/trading

LOG_DIR=~/.openclaw/logs
mkdir -p $LOG_DIR

PYTHON=/Users/openclaw/trading_env/bin/python3

$PYTHON -u -c "
import sys
import os
os.environ['OKX_API_KEY']='7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET']='AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE']='AbcD@1234'

from okx_client import grid_bot
grid_bot.GridBot().run()
" > $LOG_DIR/grid_bot.log 2>&1 &

echo "Grid Bot 已启动，PID: $!"
echo "日志: $LOG_DIR/grid_bot.log"
