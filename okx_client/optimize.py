import os
import itertools
from okx_client.backtest import MACDBacktest

def optimize():
    os.environ['OKX_API_KEY'] = '80ef8950-4469-4509-9c82-b226c0bc991c'
    os.environ['OKX_API_SECRET'] = '0E806F692183A46059817C59A59491F0'
    os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

    periods = ["1m", "5m", "15m"]
    fast_range = range(10, 15)
    slow_range = range(25, 40)
    signal_range = range(5, 10)
    
    best_results = []
    
    for bar in periods:
        for fast, slow, signal in itertools.product(fast_range, slow_range, signal_range):
            if fast >= slow: continue
            
            bt = MACDBacktest(flag="0")
            bt.fast = fast
            bt.slow = slow
            bt.signal = signal
            
            result = bt.run(days=100, bar=bar)
            summary = result.summary()
            
            with open("optimization_results.txt", "a") as f:
                f.write(f"{bar} | MACD({fast},{slow},{signal}) | 胜率: {summary['win_rate']:.2f}% | 收益: {summary['total_return']:.2f}%\n")
    
    print("\n搜索完成，结果保存在 optimization_results.txt")

if __name__ == "__main__":
    optimize()
