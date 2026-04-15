#!/bin/bash
cd ~/.openclaw/workspace/trading
source /Users/openclaw/trading_env/bin/activate

export OKX_API_KEY='7c1d51b0-0104-476c-90db-c6dff1f0b090'
export OKX_API_SECRET='AF8EB679F8AA4CE9A38C5069CB0737A7'
export OKX_PASSPHRASE='AbcD@1234'

python3 -c "
from okx_client import grid_bot
bot = grid_bot.GridBot()
bot.init_mean()
print()
bot.check_signal()
"
