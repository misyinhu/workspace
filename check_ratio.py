import os
import statistics
from datetime import datetime
os.environ['OKX_API_KEY']='7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET']='AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE']='AbcD@1234'

from okx import MarketData
m = MarketData.MarketAPI()

all_doge = []
all_eth = []
all_times = []

for bar in ['1m', '5m', '15m', '1H']:
    doge = m.get_candlesticks(instId='DOGE-USDT', bar=bar, limit=1000)
    eth = m.get_candlesticks(instId='ETH-USDT', bar=bar, limit=1000)
    
    if doge.get('code')=='0' and eth.get('code')=='0':
        for i, c in enumerate(doge['data']):
            ts = int(c[0])
            ratio = float(c[4]) / float(eth['data'][i][4])
            all_doge.append(float(c[4]))
            all_eth.append(float(eth['data'][i][4]))
            all_times.append(ts)

if all_times:
    all_times, all_doge, all_eth = zip(*sorted(zip(all_times, all_doge, all_eth)))
    
    print(f'Total: {len(all_times)} bars')
    ts_first = all_times[0]/1000
    ts_last = all_times[-1]/1000
    print(f'Range: {datetime.fromtimestamp(ts_first)} - {datetime.fromtimestamp(ts_last)}')
    
    print('\nUTC 02:10-02:30 (local 10:10-10:30):')
    for i, ts in enumerate(all_times):
        dt = datetime.fromtimestamp(ts/1000)
        if dt.hour == 2 and dt.minute >= 10 and dt.minute <= 30:
            ratio = all_doge[i] / all_eth[i]
            print(f'{dt.strftime("%Y-%m-%d %H:%M")}: {ratio:.8f}')
    
    ratios = [all_doge[i]/all_eth[i] for i in range(len(all_doge))]
    mean_96 = statistics.mean(ratios[-96:])
    current_ratio = ratios[-1]
    dev = (current_ratio - mean_96) / mean_96 * 100
    
    print(f'\n96-bar MA: {mean_96:.8f}')
    print(f'Current: {current_ratio:.8f}')
    print(f'Deviation: {dev:.2f}%')
    
    threshold = 0.015
    mean_for_long = current_ratio / (1 + threshold)
    mean_for_short = current_ratio / (1 - threshold)
    
    print(f'\nTo trigger SHORT (+1.5%): MA < {mean_for_long:.8f}')
    print(f'To trigger LONG (-1.5%): MA > {mean_for_short:.8f}')
