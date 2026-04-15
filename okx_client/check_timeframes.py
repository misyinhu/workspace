import sys
import os
os.chdir(os.path.expanduser('~/.openclaw/workspace/trading'))
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/trading'))

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx_client import OKXTrader

client = OKXTrader('1')

# 用不同周期获取数据，看哪种能获取360根
timeframes = ['1m', '5m', '15m', '1H']

for tf in timeframes:
    doge = client.get_kline('DOGE-USDT', bar=tf, limit=400)
    eth = client.get_kline('ETH-USDT', bar=tf, limit=400)
    min_len = min(len(doge['data']), len(eth['data']))
    print(f'{tf}: {min_len}根, 时间范围 {doge["data"][-1][0]} ~ {doge["data"][0][0]}')
