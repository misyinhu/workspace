import sys
import os
os.chdir(os.path.expanduser('~/.openclaw/workspace/trading'))
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/trading'))

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader

client = OKXTrader('1')

# 获取15m K线，用before分页获取更多
# 第一批
doge1 = client.get_kline('DOGE-USDT', bar='15m', limit=300)
eth1 = client.get_kline('ETH-USDT', bar='15m', limit=300)

print(f'第一批15m: {len(doge1["data"])}根')
print(f'时间范围: {doge1["data"][-1][0]} ~ {doge1["data"][0][0]}')

# 第二批 - 用最早的时间戳
earliest = doge1["data"][-1][0]
doge2 = client.get_kline('DOGE-USDT', bar='15m', limit=300, before=str(earliest))
eth2 = client.get_kline('ETH-USDT', bar='15m', limit=300, before=str(earliest))

print(f'\n第二批15m: {len(doge2["data"])}根')
print(f'时间范围: {doge2["data"][-1][0]} ~ {doge2["data"][0][0]}')

# 合并
all_doge = doge2["data"] + doge1["data"]
all_eth = eth2["data"] + eth1["data"]
print(f'\n合并后: {len(all_doge)}根')
print(f'总时间范围: {all_doge[-1][0]} ~ {all_doge[0][0]}')

# 计算
doge_prices = [float(c[4]) for c in all_doge]
eth_prices = [float(c[4]) for c in all_eth]
min_len = min(len(doge_prices), len(eth_prices))

print(f'\n可用K线对数: {min_len}')

if min_len >= 360:
    base_doge = doge_prices[min_len - 360]
    base_eth = eth_prices[min_len - 360]
    base_ratio = base_doge / base_eth
    
    # 当前
    current_ratio = doge_prices[-1] / eth_prices[-1]
    current_dev = (current_ratio - base_ratio) / base_ratio * 100
    
    print(f'\n基准(360根K线前):')
    print(f'  DOGE: {base_doge}')
    print(f'  ETH: {base_eth}')
    print(f'  比率: {base_ratio:.8f}')
    print(f'\n当前:')
    print(f'  DOGE: {doge_prices[-1]}')
    print(f'  ETH: {eth_prices[-1]}')
    print(f'  比率: {current_ratio:.8f}')
    print(f'  偏离: {current_dev:+.2f}%')
    
    # 找10:16的数据
    for i, k in enumerate(all_doge):
        if '10:16' in k[0]:
            r = doge_prices[i] / eth_prices[i]
            dev = (r - base_ratio) / base_ratio * 100
            print(f'\n10:16:')
            print(f'  比率: {r:.8f}')
            print(f'  偏离: {dev:+.2f}%')
            print(f'  触发入场: {"是" if abs(dev) >= 1.5 else "否"}')
            break
