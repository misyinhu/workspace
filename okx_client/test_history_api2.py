import os
os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

import sys
home = os.path.expanduser('~/.openclaw/workspace/trading')
sys.path.insert(0, home)
os.chdir(home)

from okx_client import OKXTrader
from datetime import datetime, timedelta

client = OKXTrader('1')

# 尝试用after参数从更早时间开始获取
# 10:16 = 2026-03-15 10:16:00
# 用after参数获取10:16之后的数据
target = datetime(2026, 3, 15, 10, 16, 0)
ts_target = int(target.timestamp() * 1000)

print(f'目标时间: {target}')
print(f'目标时间戳: {ts_target}')

# Get after 10:16
doge = client.get_history_kline('DOGE-USDT', bar='1m', limit=300, after=str(ts_target))
print(f'\n使用after参数:')
print(f'Code: {doge.get("code")}')

if doge.get('code') == '0' and doge.get('data'):
    print(f'数据条数: {len(doge["data"])}')
    if len(doge["data"]) > 0:
        print(f'时间范围: {datetime.fromtimestamp(int(doge["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge["data"][0][0])/1000)}')
else:
    print(f'Error: {doge.get("msg")}')

# Try getting 15m bars
print('\n\n使用15m周期:')
doge15 = client.get_history_kline('DOGE-USDT', bar='15m', limit=300)
print(f'Code: {doge15.get("code")}')

if doge15.get('code') == '0' and doge15.get('data'):
    print(f'数据条数: {len(doge15["data"])}')
    if len(doge15["data"]) > 0:
        print(f'时间范围: {datetime.fromtimestamp(int(doge15["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge15["data"][0][0])/1000)}')
else:
    print(f'Error: {doge15.get("msg")}')
