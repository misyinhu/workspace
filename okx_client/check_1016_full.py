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

# 获取360根1m K线数据
def get_with_history(inst_id, target=360):
    all_data = []
    before = None
    while len(all_data) < target:
        remaining = target - len(all_data)
        data = client.get_kline(inst_id, bar='1m', limit=min(300, remaining), before=before)
        if data.get('code') != '0' or not data.get('data'):
            break
        all_data.extend(data['data'])
        before = data['data'][-1][0]
        if len(data['data']) < 300:
            break
    return all_data

doge = get_with_history('DOGE-USDT', 360)
eth = get_with_history('ETH-USDT', 360)

print(f'总数据: {len(doge)} 根')
print(f'时间范围: {datetime.fromtimestamp(int(doge[-1][0])/1000)} ~ {datetime.fromtimestamp(int(doge[0][0])/1000)}')

# 找10:16
for i, k in enumerate(doge):
    ts = int(k[0])
    dt = datetime.fromtimestamp(ts/1000)
    if dt.hour == 10 and dt.minute == 16:
        doge_p = float(k[4])
        eth_p = float(eth[i][4])
        ratio = doge_p / eth_p
        
        # 基准: 360根前
        base_doge = float(doge[-1][4])
        base_eth = float(eth[-1][4])
        base_ratio = base_doge / base_eth
        
        dev = (ratio - base_ratio) / base_ratio * 100
        print(f'\n10:16 数据:')
        print(f'  时间: {dt}')
        print(f'  DOGE: {doge_p}')
        print(f'  ETH: {eth_p}')
        print(f'  比率: {ratio:.8f}')
        print(f'  基准(360根前): {base_ratio:.8f}')
        print(f'  偏离: {dev:+.2f}%')
        entry = "是" if abs(dev) >= 1.5 else "否"
        print(f'  触发入场: {entry}')
        break
