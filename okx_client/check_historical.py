import sys
import os
os.chdir(os.path.expanduser('~/.openclaw/workspace/trading'))
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/trading'))

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader
from datetime import datetime

client = OKXTrader('1')

# 先获取最新的300根
doge = client.get_kline('DOGE-USDT', bar='1m', limit=300)
print(f'最新300根时间范围: {doge["data"][-1][0]} ~ {doge["data"][0][0]}')

# 用最早的时间戳去获取更早的数据
earliest_ts = doge["data"][-1][0]  # 最早的K线时间戳
print(f'最早时间戳: {earliest_ts}')

# 用before参数获取更早的数据
doge_hist = client.get_kline('DOGE-USDT', bar='1m', limit=300, before=earliest_ts)
print(f'\n历史300根时间范围: {doge_hist["data"][-1][0]} ~ {doge_hist["data"][0][0]}')

# 合并数据
all_doge = doge_hist["data"] + doge["data"]
print(f'\n合并后总量: {len(all_doge)}')
print(f'最早: {all_doge[-1][0]}')
print(f'最新: {all_doge[0][0]}')

# ETH同理
eth = client.get_kline('DOGE-USDT', bar='1m', limit=300)
earliest_ts = eth["data"][-1][0]
eth_hist = client.get_kline('ETH-USDT', bar='1m', limit=300, before=earliest_ts)
all_eth = eth_hist["data"] + eth["data"]
print(f'\nETH合并后总量: {len(all_eth)}')
print(f'最早: {all_eth[-1][0]}')

# 计算10:16的基准
doge_prices = [float(c[4]) for c in all_doge]
eth_prices = [float(c[4]) for c in all_eth]

min_len = min(len(doge_prices), len(eth_prices))
print(f'\n可用的K线对数: {min_len}')

# 基准价格: 360根K线前
if min_len >= 360:
    base_doge = doge_prices[min_len - 360]
    base_eth = eth_prices[min_len - 360]
    base_ratio = base_doge / base_eth
    print(f'基准DOGE价格(360根前): {base_doge}')
    print(f'基准ETH价格(360根前): {base_eth}')
    print(f'基准比率: {base_ratio:.8f}')
    
    # 找10:16对应的K线
    for i, k in enumerate(all_doge):
        if '10:16' in k[0]:
            ratio_1016 = doge_prices[i] / eth_prices[i]
            dev_1016 = (ratio_1016 - base_ratio) / base_ratio * 100
            print(f'\n10:16 比率: {ratio_1016:.8f}')
            print(f'10:16 偏离基准: {dev_1016:+.2f}%')
            print(f'10:16 是否触发入场: {"是" if abs(dev_1016) >= 1.5 else "否"}')
            break
else:
    print(f'数据不足360根，只有{min_len}根')
