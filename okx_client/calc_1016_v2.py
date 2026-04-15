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

# 用after获取更多数据 - 目标时间设为更早
# 10:16 - 6小时 = 04:16
target = datetime(2026, 3, 15, 4, 16, 0)
ts_target = int(target.timestamp() * 1000)

print(f'目标时间: {target}')

# 获取10:16之前的数据
doge = client.get_history_kline('DOGE-USDT', bar='1m', limit=400, after=str(ts_target))
eth = client.get_history_kline('ETH-USDT', bar='1m', limit=400, after=str(ts_target))

print(f'DOGE数据: {len(doge["data"])}条')
print(f'ETH数据: {len(eth["data"])}条')

if doge.get('code') == '0' and eth.get('code') == '0':
    doge_prices = [float(c[4]) for c in doge['data']]
    eth_prices = [float(c[4]) for c in eth['data']]
    
    min_len = min(len(doge_prices), len(eth_prices))
    print(f'\n可用K线: {min_len}根')
    print(f'时间范围: {datetime.fromtimestamp(int(doge["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge["data"][0][0])/1000)}')
    
    if min_len >= 360:
        base_doge = doge_prices[-1]
        base_eth = eth_prices[-1]
        base_ratio = base_doge / base_eth
        
        print(f'\n基准(360根K线前):')
        print(f'  DOGE: {base_doge}')
        print(f'  ETH: {base_eth}')
        print(f'  比率: {base_ratio:.8f}')
        
        # 找10:16
        for i, k in enumerate(doge['data']):
            ts = int(k[0])
            dt = datetime.fromtimestamp(ts/1000)
            if dt.hour == 10 and dt.minute == 16:
                ratio_1016 = doge_prices[i] / eth_prices[i]
                dev = (ratio_1016 - base_ratio) / base_ratio * 100
                print(f'\n10:16:')
                print(f'  DOGE: {doge_prices[i]}')
                print(f'  ETH: {eth_prices[i]}')
                print(f'  比率: {ratio_1016:.8f}')
                print(f'  偏离: {dev:+.2f}%')
                entry = "是" if abs(dev) >= 1.5 else "否"
                print(f'  触发入场: {entry}')
                break
