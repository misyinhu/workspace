import sys
import os
os.chdir(os.path.expanduser('~/.openclaw/workspace/trading'))
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/trading'))

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader

client = OKXTrader('1')

doge = client.get_kline('DOGE-USDT', bar='1m', limit=400)
eth = client.get_kline('ETH-USDT', bar='1m', limit=400)

doge_prices = [float(c[4]) for c in doge['data']]
eth_prices = [float(c[4]) for c in eth['data']]

min_len = min(len(doge_prices), len(eth_prices))

print(f'K线数量: {min_len}')
print(f'最早时间: {doge["data"][-1][0]}')
print(f'最新时间: {doge["data"][0][0]}')
print(f'最早DOGE: {doge_prices[0]:.5f}')
print(f'最早ETH: {eth_prices[0]:.2f}')
print(f'最新DOGE: {doge_prices[-1]:.5f}')
print(f'最新ETH: {eth_prices[-1]:.2f}')

base_ratio = doge_prices[0] / eth_prices[0]
current_ratio = doge_prices[-1] / eth_prices[-1]

print(f'基准比率(最早K线): {base_ratio:.8f}')
print(f'当前比率: {current_ratio:.8f}')
print(f'当前偏离: {(current_ratio-base_ratio)/base_ratio*100:+.2f}%')

for i, k in enumerate(doge['data']):
    if '10:16' in k[0]:
        print(f'10:16 DOGE: {doge_prices[i]:.5f}')
        print(f'10:16 ETH: {eth_prices[i]:.2f}')
        ratio_1016 = doge_prices[i] / eth_prices[i]
        print(f'10:16 比率: {ratio_1016:.8f}')
        print(f'10:16 偏离基准: {(ratio_1016-base_ratio)/base_ratio*100:+.2f}%')
        break
