import os
import sys
home = os.path.expanduser('~/.openclaw/workspace/trading')
os.chdir(home)
sys.path.insert(0, home)

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader

client = OKXTrader('1')

# 模拟分页获取
def get_candles_with_history(inst_id, bar="1m", target_count=360):
    all_prices = []
    before_ts = None
    
    while len(all_prices) < target_count:
        remaining = target_count - len(all_prices)
        batch_size = min(300, remaining)
        
        data = client.get_kline(inst_id, bar=bar, limit=batch_size, before=before_ts)
        if data.get("code") != "0" or not data.get("data"):
            print(f"API error: {data}")
            break
            
        prices = [float(c[4]) for c in data["data"]]
        all_prices.extend(prices)
        
        before_ts = data["data"][-1][0]
        
        print(f"获取 {len(prices)} 根, 累计 {len(all_prices)} 根")
        
        if len(prices) < batch_size:
            break
    
    return all_prices

print("获取DOGE历史数据...")
doge = get_candles_with_history("DOGE-USDT", bar="1m", target_count=360)
print(f"DOGE总计: {len(doge)} 根")

print("\n获取ETH历史数据...")
eth = get_candles_with_history("ETH-USDT", bar="1m", target_count=360)
print(f"ETH总计: {len(eth)} 根")

min_len = min(len(doge), len(eth))
print(f"\n可用K线对数: {min_len}")

if min_len >= 360:
    base_doge = doge[0]
    base_eth = eth[0]
    base_ratio = base_doge / base_eth
    
    current_ratio = doge[-1] / eth[-1]
    current_dev = (current_ratio - base_ratio) / base_ratio * 100
    
    print(f"\n基准(360根K线前):")
    print(f"  DOGE: {base_doge}")
    print(f"  ETH: {base_eth}")
    print(f"  比率: {base_ratio:.8f}")
    print(f"\n当前:")
    print(f"  比率: {current_ratio:.8f}")
    print(f"  偏离: {current_dev:+.2f}%")
    
    # 找10:16的数据
    # 需要重新获取带时间戳的数据
    data = client.get_kline("DOGE-USDT", bar="1m", limit=300)
    for i, k in enumerate(data["data"]):
        ts = int(k[0])
        from datetime import datetime
        dt = datetime.fromtimestamp(ts/1000)
        if dt.hour == 10 and dt.minute == 16:
            # 获取对应时间的ETH价格
            eth_data = client.get_kline("ETH-USDT", bar="1m", limit=300)
            eth_p = float(eth_data["data"][i][4])
            doge_p = float(k[4])
            ratio = doge_p / eth_p
            dev = (ratio - base_ratio) / base_ratio * 100
            print(f"\n10:16:")
            print(f"  DOGE: {doge_p}")
            print(f"  ETH: {eth_p}")
            print(f"  比率: {ratio:.8f}")
            print(f"  偏离: {dev:+.2f}%")
            print(f"  触发入场: {'是' if abs(dev) >= 1.5 else '否'}")
            break
else:
    print(f"数据不足360根，只有{min_len}根")
