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

ts_target = 1773540960000  # 10:16

# 获取两批数据
doge1 = client.get_history_kline('DOGE-USDT', bar='1m', limit=300, after=str(ts_target))
eth1 = client.get_history_kline('ETH-USDT', bar='1m', limit=300, after=str(ts_target))

last_ts = doge1["data"][-1][0]
doge2 = client.get_history_kline('DOGE-USDT', bar='1m', limit=300, after=last_ts)
eth2 = client.get_history_kline('ETH-USDT', bar='1m', limit=300, after=last_ts)

# 合并: [更老, ..., 较新] + [更老, ..., 较新]
# 数据本身是倒序的(最新在前)，所以直接拼接
doge_data = doge1["data"] + doge2["data"]
eth_data = eth1["data"] + eth2["data"]

print(f'总数据: {len(doge_data)}条')
# 第一条是最新，最后一条是最老
first_ts = int(doge_data[0][0])
last_ts = int(doge_data[-1][0])
print(f'时间范围(倒序): {datetime.fromtimestamp(first_ts/1000)} ~ {datetime.fromtimestamp(last_ts/1000)}')

# 取价格 (最新在前)
doge_prices = [float(c[4]) for c in doge_data]
eth_prices = [float(c[4]) for c in eth_data]

# 基准: 第360根(从后往前数第360个，即索引359)
# doge_prices[0]是最新的，doge_prices[359]是第360根(从新往老数)
base_doge = doge_prices[359]
base_eth = eth_prices[359]
base_ratio = base_doge / base_eth

print(f'\n基准(360根K线前):')
print(f'  DOGE: {base_doge}')
print(f'  ETH: {base_eth}')
print(f'  比率: {base_ratio:.8f}')

# 找10:16 (doge_data[0]是最新的，向后找10:16)
for i, k in enumerate(doge_data):
    ts = int(k[0])
    dt = datetime.fromtimestamp(ts/1000)
    if dt.hour == 10 and dt.minute == 16:
        ratio_1016 = doge_prices[i] / eth_prices[i]
        dev = (ratio_1016 - base_ratio) / base_ratio * 100
        print(f'\n10:16:')
        print(f'  位置: 从新到老第{i}根')
        print(f'  DOGE: {doge_prices[i]}')
        print(f'  ETH: {eth_prices[i]}')
        print(f'  比率: {ratio_1016:.8f}')
        print(f'  偏离: {dev:+.2f}%')
        entry = "是" if abs(dev) >= 1.5 else "否"
        print(f'  触发入场: {entry}')
        break
else:
    print('\n没有找到10:16，看看10点的:')
    for i, k in enumerate(doge_data[:10]):
        ts = int(k[0])
        dt = datetime.fromtimestamp(ts/1000)
        if dt.hour == 10:
            r = doge_prices[i] / eth_prices[i]
            d = (r - base_ratio) / base_ratio * 100
            print(f'  {dt}: 比率={r:.8f}, 偏离={d:+.2f}%')
