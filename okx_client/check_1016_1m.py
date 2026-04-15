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
doge = client.get_kline('DOGE-USDT', bar='1m', limit=300)
eth = client.get_kline('ETH-USDT', bar='1m', limit=300)

print(f'时间范围: {datetime.fromtimestamp(int(doge["data"][-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge["data"][0][0])/1000)}')

# 找10:16
for i, k in enumerate(doge['data']):
    ts = int(k[0])
    dt = datetime.fromtimestamp(ts/1000)
    if dt.hour == 10 and dt.minute == 16:
        doge_p = float(k[4])
        eth_p = float(eth['data'][i][4])
        ratio = doge_p / eth_p
        
        # 基准: 360根前
        base_doge = 0.097
        base_eth = 2109.28
        base_ratio = base_doge / base_eth
        
        dev = (ratio - base_ratio) / base_ratio * 100
        print(f'10:16:')
        print(f'  DOGE: {doge_p}')
        print(f'  ETH: {eth_p}')
        print(f'  比率: {ratio:.8f}')
        print(f'  基准: {base_ratio:.8f}')
        print(f'  偏离: {dev:+.2f}%')
        entry = "是" if abs(dev) >= 1.5 else "否"
        print(f'  触发入场: {entry}')
        break
else:
    print('没有找到10:16的数据')
