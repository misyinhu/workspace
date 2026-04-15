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

# 测试历史K线API
# today is 2026-03-15
# 10:16 is about 5 hours ago
# Let's get 1m bars from yesterday

# 10:16 today timestamp
target = datetime(2026, 3, 15, 10, 16, 0)
ts_target = int(target.timestamp() * 1000)

# Get history candles before 10:16
print(f'获取10:16之前的历史K线...')
doge = client.get_history_kline('DOGE-USDT', bar='1m', limit=300, before=str(ts_target))
print(f'DOGE: {doge.get("code")}')

if doge.get('code') == '0' and doge.get('data'):
    print(f'数据条数: {len(doge["data"])}')
    print(f'时间范围: {doge["data"][-1][0]} ~ {doge["data"][0][0]}')
    print(f'时间范围: {datetime.fromtimestamp(int(doge["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge["data"][0][0])/1000)}')
else:
    print(f'Error: {doge.get("msg")}')
