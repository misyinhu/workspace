#!/usr/bin/env python3
"""
DOGE/ETH 比率网格交易机器人
"""
import os, sys, time, statistics
from datetime import datetime

sys.path.insert(0, '/Users/wang/miniconda3/lib/python3.13/site-packages')

os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'

from okx import MarketData

CONFIG = {
    "DEMO": True, 
    "THRESHOLD": 0.015, 
    "HOLDING_PERIOD": 7200, 
    "CHECK_INTERVAL": 15, 
    "MARGIN": 400, 
    "LEVERAGE": 10,
    "DOGE": "DOGE-USDT", 
    "ETH": "ETH-USDT"
}

class OKXClient:
    def __init__(self, demo=True):
        self.market = MarketData.MarketAPI(flag="1" if demo else "0")
    
    def get_ticker(self, inst_id):
        try:
            data = self.market.get_ticker(instId=inst_id)
            if data.get("code") == "0" and data.get("data"):
                return float(data["data"][0]["last"])
        except Exception as e:
            print(f"错误: {e}")
        return None
    
    def get_candles(self, inst_id, bar="1H", limit=100):
        try:
            data = self.market.get_candlesticks(instId=inst_id, bar=bar, limit=limit)
            if data.get("code") == "0" and data.get("data"):
                return [float(c[4]) for c in data["data"]]
        except Exception as e:
            print(f"错误: {e}")
        return []

class GridBot:
    def __init__(self):
        self.client = OKXClient(CONFIG["DEMO"])
        self.mean_ratio = 0
        self.position = None   # None, "long", "short"
        self.entry_time = 0
        self.entry_ratio = 0
        
    def init_mean(self):
        print("获取历史数据...")
        doge_c = self.client.get_candles(CONFIG["DOGE"])
        eth_c = self.client.get_candles(CONFIG["ETH"])
        if doge_c and eth_c:
            ratios = [eth_c[i]/doge_c[i] for i in range(len(doge_c))]
            self.mean_ratio = statistics.mean(ratios[-96:])
            print(f"96小时均值: {self.mean_ratio:.0f}")
    
    def check_signal(self):
        doge = self.client.get_ticker(CONFIG["DOGE"])
        eth = self.client.get_ticker(CONFIG["ETH"])
        if not doge or not eth:
            print("获取价格失败")
            return
        
        ratio = eth/doge
        dev = (ratio-self.mean_ratio)/self.mean_ratio*100
        
        # 计算信号方向
        # dev < -1.5%: 做多DOGE + 做空ETH (long)
        # dev > +1.5%: 做空DOGE + 做多ETH (short)
        
        signal = None
        if dev < -1.5:
            signal = "long"   # 比率低，做多DOGE + 做空ETH
        elif dev > 1.5:
            signal = "short"  # 比率高，做空DOGE + 做多ETH
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"DOGE:${doge:.5f} ETH:${eth:.2f} 比率:{ratio:.0f} 偏离:{dev:+.2f}% "
              f"持仓:{self.position if self.position else '无'}")
        
        # ====== 持仓管理逻辑 ======
        
        # 情况1: 无持仓，有信号 -> 入场
        if not self.position and signal:
            self.enter(signal, ratio)
        
        # 情况2: 有持仓，无信号 -> 检查出场
        elif self.position and not signal:
            self.check_exit(ratio, dev)
        
        # 情况3: 有持仓，有信号 -> 检查是否需要换仓
        elif self.position and signal:
            if self.position == signal:
                # 方向一致，保留持仓
                self.check_exit(ratio, dev)
            else:
                # 方向不一致，先平仓再入场
                print(f"\n[换仓] 持仓方向: {self.position} -> 新信号: {signal}")
                print("先平仓...")
                self.exit(ratio, reason="换仓")
                print("再入场...")
                self.enter(signal, ratio)
    
    def check_exit(self, ratio, dev):
        """检查是否出场"""
        elapsed = time.time() - self.entry_time
        
        # 出场条件: 时间到 或 回归均值
        time_up = elapsed >= CONFIG["HOLDING_PERIOD"]
        back_to_mean = False
        
        if self.position == "long" and dev >= -0.2:
            back_to_mean = True  # 比率回升
        elif self.position == "short" and dev <= 0.2:
            back_to_mean = True  # 比率回落
        
        if time_up:
            self.exit(ratio, reason="时间到期")
        elif back_to_mean:
            self.exit(ratio, reason="回归均值")
    
    def enter(self, pos, ratio):
        """入场"""
        print(f"\n{'='*50}")
        print(f"[入场] {pos} 比率:{ratio:.0f}")
        print(f"{'='*50}")
        
        doge = self.client.get_ticker(CONFIG["DOGE"])
        eth = self.client.get_ticker(CONFIG["ETH"])
        
        each = CONFIG["MARGIN"] * CONFIG["LEVERAGE"] / 2
        
        if pos == "long":
            # 做多DOGE + 做空ETH
            doge_qty = each / doge
            eth_qty = each / eth
            print(f"做多DOGE: {doge_qty:.0f} ≈ ${each}")
            print(f"做空ETH: {eth_qty:.4f} ≈ ${each}")
        else:
            # 做空DOGE + 做多ETH
            doge_qty = each / doge
            eth_qty = each / eth
            print(f"做空DOGE: {doge_qty:.0f} ≈ ${each}")
            print(f"做多ETH: {eth_qty:.4f} ≈ ${each}")
        
        self.position = pos
        self.entry_time = time.time()
        self.entry_ratio = ratio
    
    def exit(self, ratio, reason="出场"):
        """出场"""
        if self.position == "long":
            profit = (ratio - self.entry_ratio) / self.entry_ratio * 100
        else:
            profit = (self.entry_ratio - ratio) / self.entry_ratio * 100
        
        print(f"\n{'='*50}")
        print(f"[{reason}] 比率:{ratio:.0f} 盈亏:{profit:+.2f}%")
        print(f"{'='*50}\n")
        
        self.position = None
        self.entry_time = 0
        self.entry_ratio = 0
    
    def run(self):
        print("="*50 + " DOGE/ETH 网格交易机器人 " + "="*50)
        print(f"模式: {'模拟盘' if CONFIG['DEMO'] else '实盘'}")
        print(f"入场阈值: ±{CONFIG['THRESHOLD']*100}%")
        print(f"持仓时间: {CONFIG['HOLDING_PERIOD']/60}分钟")
        print("="*50)
        
        self.init_mean()
        print("\n开始监控 (按Ctrl+C停止)...\n")
        
        while True:
            try:
                self.check_signal()
                time.sleep(CONFIG["CHECK_INTERVAL"])
            except KeyboardInterrupt:
                print("\n机器人停止")
                break
            except Exception as e:
                print(f"错误: {e}")
                time.sleep(CONFIG["CHECK_INTERVAL"])

GridBot().run()
