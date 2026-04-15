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

# 目标: 获取从 10:16 到现在的完整1分钟K线数据
# 10:16 = 1773540960000
# 现在 = 约 177357xxx

# 用history API的after参数获取10:16之后的数据
# after = 获取该时间之后的数据（更接近现在）
ts_target = 1773540960000  # 10:16

# 第一次: 获取10:16到现在的数据
doge1 = client.get_history_kline('DOGE-USDT', bar='1m', limit=300, after=str(ts_target))
print(f'第一批: {len(doge1["data"])}条')

if len(doge1["data"]) == 300:
    # 需要第二批
    # 用最后一条的时间戳继续获取
    last_ts = doge1["data"][-1][0]
    doge2 = client.get_history_kline('DOGE-USDT', bar='1m', limit=300, after=last_ts)
    print(f'第二批: {len(doge2["data"])}条')
    
    # 合并
    all_data = doge1["data"] + doge2["data"]
else:
    all_data = doge1["data"]

print(f'总数据: {len(all_data)}条')

if len(all_data) > 0:
    first_ts = int(all_data[0][0])
    last_ts = int(all_data[-1][0])
    print(f'时间范围: {datetime.fromtimestamp(first_ts/1000)} ~ {datetime.fromtimestamp(last_ts/1000)}')
