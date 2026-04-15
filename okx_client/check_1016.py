import sys
import os
os.chdir(os.path.expanduser('~/.openclaw/workspace/trading'))
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/trading'))

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader

client = OKXTrader('1')

# 直接获取300根15m
doge = client.get_kline('DOGE-USDT', bar='15m', limit=300)
eth = client.get_kline('ETH-USDT', bar='15m', limit=300)

# 找10:16的K线
for i, k in enumerate(doge['data']):
    if '10:16' in k[0]:
        doge_p = float(doge['data'][i][4])
        eth_p = float(eth['data'][i][4])
        print(f'找到10:16: DOGE={doge_p}, ETH={eth_p}')
        
        # 计算基准
        doge_prices = [float(c[4]) for c in doge['data']]
        eth_prices = [float(c[4]) for c in eth['data']]
        
        base_doge = doge_prices[0]
        base_eth = eth_prices[0]
        base_ratio = base_doge / base_eth
        
        ratio_1016 = doge_p / eth_p
        dev = (ratio_1016 - base_ratio) / base_ratio * 100
        
        print(f'基准比率: {base_ratio:.8f}')
        print(f'10:16比率: {ratio_1016:.8f}')
        print(f'10:16偏离: {dev:+.2f}%')
        print(f'是否触发入场: {"是" if abs(dev) >= 1.5 else "否"}')
        break
else:
    print('没有找到10:16的K线')
    print(f'K线时间列表:')
    for k in doge['data'][:5]:
        print(f'  {k[0]}')
    print('...')
    for k in doge['data'][-5:]:
        print(f'  {k[0]}')
