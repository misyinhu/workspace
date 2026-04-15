import os
os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

import sys
home = os.path.expanduser('~/.openclaw/workspace/trading')
sys.path.insert(0, home)
os.chdir(home)

from okx_client import OKXTrader
from datetime import datetime

client = OKXTrader('1')

# 获取第一批
doge1 = client.get_kline('DOGE-USDT', bar='1m', limit=300)
print(f'第一批: {len(doge1["data"])}根')
print(f'时间: {doge1["data"][-1][0]} ~ {doge1["data"][0][0]}')
print(f'时间: {datetime.fromtimestamp(int(doge1["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge1["data"][0][0])/1000)}')

# 用before获取第二批
before = doge1["data"][-1][0]
doge2 = client.get_kline('DOGE-USDT', bar='1m', limit=300, before=str(before))
print(f'\n第二批: {len(doge2["data"])}根')
print(f'时间: {doge2["data"][-1][0]} ~ {doge2["data"][0][0]}')
print(f'时间: {datetime.fromtimestamp(int(doge2["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge2["data"][0][0])/1000)}')
