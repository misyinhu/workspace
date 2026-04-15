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

# 测试: after参数到底返回什么?
# after=10:16 → 返回 10:16 ~ 更早 (oldest first)
ts_1016 = 1773540960000

doge = client.get_history_kline('DOGE-USDT', bar='1m', limit=10, after=str(ts_1016))
print('after=10:16:')
for k in doge['data']:
    print(f'  {datetime.fromtimestamp(int(k[0])/1000)}')

# before=10:16 → 返回 10:16 ~ 最新 (newest first)  
doge2 = client.get_history_kline('DOGE-USDT', bar='1m', limit=10, before=str(ts_1016))
print('\nbefore=10:16:')
for k in doge2['data']:
    print(f'  {datetime.fromtimestamp(int(k[0])/1000)}')
