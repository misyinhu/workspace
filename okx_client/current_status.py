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

# 获取当前可用的300根1分钟K线
doge = client.get_kline('DOGE-USDT', bar='1m', limit=300)
eth = client.get_kline('ETH-USDT', bar='1m', limit=300)

doge_prices = [float(c[4]) for c in doge['data']]
eth_prices = [float(c[4]) for c in eth['data']]

first_ts = int(doge["data"][-1][0])
last_ts = int(doge["data"][0][0])
print(f'数据范围: {datetime.fromtimestamp(first_ts/1000)} ~ {datetime.fromtimestamp(last_ts/1000)}')

base_ratio = doge_prices[0] / eth_prices[0]
current_ratio = doge_prices[-1] / eth_prices[-1]
current_dev = (current_ratio - base_ratio) / base_ratio * 100

print(f'\n基准(300根K线前): {base_ratio:.8f}')
print(f'当前: {current_ratio:.8f}')
print(f'当前偏离: {current_dev:+.2f}%')

print('\n注意: 模拟盘API仅保留约5小时数据')
print('10:16 (约5.5小时前) 不在数据范围内')
print('如需查看更早历史数据，需使用实盘API')
