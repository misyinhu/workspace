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

# 用after=10:17获取10:16及之前的数据
# 10:16的K线形成于10:17，所以用after=10:17
ts_1017 = 1773541020000  # 10:17

doge = client.get_history_kline('DOGE-USDT', bar='1m', limit=400, after=str(ts_1017))
eth = client.get_history_kline('ETH-USDT', bar='1m', limit=400, after=str(ts_1017))

doge_prices = [float(c[4]) for c in doge['data']]
eth_prices = [float(c[4]) for c in eth['data']]

print(f'数据条数: {len(doge_prices)}')

first_ts = int(doge["data"][0][0])
last_ts = int(doge["data"][-1][0])
print(f'时间范围: {datetime.fromtimestamp(first_ts/1000)} ~ {datetime.fromtimestamp(last_ts/1000)}')

if len(doge_prices) >= 360:
    # 基准: 第360根(最早)
    base_doge = doge_prices[0]
    base_eth = eth_prices[0]
    base_ratio = base_doge / base_eth
    
    print(f'\n基准(360根K线前):')
    print(f'  DOGE: {base_doge}')
    print(f'  ETH: {base_eth}')
    print(f'  比率: {base_ratio:.8f}')
    
    # 找10:16(实际是10:16:00这根开始形成的K线)
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
else:
    print(f'数据不足360根，只有{len(doge_prices)}根')
