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

# 获取当前最新的300根
doge = client.get_kline('DOGE-USDT', bar='1m', limit=300)
eth = client.get_kline('ETH-USDT', bar='1m', limit=300)

doge_prices = [float(c[4]) for c in doge['data']]
eth_prices = [float(c[4]) for c in eth['data']]

# 基准是第300根(最早)
base_ratio = doge_prices[0] / eth_prices[0]

print(f'基准(300根K线前): {base_ratio:.8f}')
print(f'时间范围: {datetime.fromtimestamp(int(doge["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge["data"][0][0])/1000)}')

# 检查所有数据点的偏离
max_dev = 0
max_dev_idx = 0
for i in range(len(doge_prices)):
    r = doge_prices[i] / eth_prices[i]
    dev = (r - base_ratio) / base_ratio * 100
    if abs(dev) > abs(max_dev):
        max_dev = dev
        max_dev_idx = i

print(f'\n最大偏离: {max_dev:+.2f}%')
print(f'位置: 第{max_dev_idx}根')
ts = int(doge["data"][max_dev_idx][0])
print(f'时间: {datetime.fromtimestamp(ts/1000)}')
print(f'触发入场: {"是" if abs(max_dev) >= 1.5 else "否"}')
