import os
os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

import sys
home = os.path.expanduser('~/.openclaw/workspace/trading')
sys.path.insert(0, home)
os.chdir(home)

from okx_client.grid_bot import GridBot

bot = GridBot()
doge = bot.get_candles_with_history('DOGE-USDT', bar='1m', target_count=360)
print(f'获取到 {len(doge)} 根DOGE价格')
