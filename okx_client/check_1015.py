import os
import sys
home = os.path.expanduser('~/.openclaw/workspace/trading')
os.chdir(home)
sys.path.insert(0, home)

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader
from datetime import datetime

client = OKXTrader('1')
doge = client.get_kline('DOGE-USDT', bar='15m', limit=300)
eth = client.get_kline('ETH-USDT', bar='15m', limit=300)

# 找10:15的K线 (10:16会落在10:15-10:30这个15分钟区间)
for i, k in enumerate(doge['data']):
    ts = int(k[0])
    dt = datetime.fromtimestamp(ts/1000)
    if dt.hour == 10 and dt.minute == 15:
        print(f'找到10:15 K线: {dt}')
        print(f'  DOGE: {k[4]}')
        print(f'  ETH: {eth["data"][i][4]}')
        
        # 用360根前的价格作为基准
        doge_prices = [float(c[4]) for c in doge['data']]
        eth_prices = [float(c[4]) for c in eth['data']]
        
        base_doge = doge_prices[0]
        base_eth = eth_prices[0]
        base_ratio = base_doge / base_eth
        
        ratio_1015 = float(k[4]) / float(eth['data'][i][4])
        dev = (ratio_1015 - base_ratio) / base_ratio * 100
        
        print(f'  基准比率: {base_ratio:.8f}')
        print(f'  10:15比率: {ratio_1015:.8f}')
        print(f'  10:15偏离: {dev:+.2f}%')
        entry = "是" if abs(dev) >= 1.5 else "否"
        print(f'  是否触发入场: {entry}')
        break
