"""DOGE MACD 策略模块"""

import os
import sys
from typing import Optional, Dict, List
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from okx_client import OKXTrader


class MACDStrategy:
    def __init__(self, flag: str = "1"):
        self.client = OKXTrader(flag)
        self.inst_id = "DOGE-USDT"
        
        self.fast = 8
        self.slow = 21
        self.signal = 5
        
        self.stop_loss_pct = 0.018
        self.take_profit_pct = 0.027
        
        self.position = None
        self.entry_price = 0
        self.entry_time = None
        
        self.trailing_stop_pct = 0.015
    
    def calculate_ema(self, values: List[float], period: int) -> Optional[float]:
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = values[0]
        for value in values[1:]:
            ema = (value - ema) * multiplier + ema
        return ema
    
    def calculate_macd(self, closes: List[float]) -> Dict:
        if len(closes) < self.slow + self.signal:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        fast_ema = self.calculate_ema(closes, self.fast)
        slow_ema = self.calculate_ema(closes, self.slow)
        
        if fast_ema is None or slow_ema is None:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        macd_line = fast_ema - slow_ema
        
        macd_values = []
        for i in range(len(closes) - self.signal + 1):
            f = self.calculate_ema(closes[i:i+self.fast], self.fast)
            s = self.calculate_ema(closes[i:i+self.slow], self.slow)
            if f and s:
                macd_values.append(f - s)
        
        if len(macd_values) < self.signal:
            return {'macd': macd_line, 'signal': 0, 'histogram': macd_line}
        
        signal_line = self.calculate_ema(macd_values, self.signal)
        histogram = macd_line - signal_line if signal_line else 0
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def get_signal(self) -> str:
        ohlc = self.client.get_ohlc(self.inst_id, bar="1H", limit=50)
        if not ohlc:
            return "hold"
        
        closes = [c['close'] for c in ohlc]
        closes.reverse()
        
        macd = self.calculate_macd(closes)
        
        if macd['histogram'] > 0 and macd['macd'] > macd['signal']:
            return "long"
        elif macd['histogram'] < 0 and macd['macd'] < macd['signal']:
            return "short"
        return "hold"
    
    def calculate_position_size(self, account_balance: float, risk_pct: float = 0.02) -> float:
        atr = self.client.calculate_atr(self.inst_id, period=14, bar="1H")
        if atr is None:
            atr = self.client.get_ticker(self.inst_id)
            if atr.get("code") == "0":
                last_price = float(atr["data"][0]["last"])
                atr = last_price * 0.02
            
        risk_amount = account_balance * risk_pct
        position_size = risk_amount / atr if atr else risk_amount / (account_balance * 0.02)
        
        return min(position_size, account_balance * 0.1)
    
    def check_stop_loss(self, current_price: float) -> bool:
        if not self.position or not self.entry_price:
            return False
        
        if self.position == "long":
            loss_pct = (self.entry_price - current_price) / self.entry_price
            return loss_pct >= self.stop_loss_pct
        else:
            loss_pct = (current_price - self.entry_price) / self.entry_price
            return loss_pct >= self.stop_loss_pct
    
    def check_take_profit(self, current_price: float) -> bool:
        if not self.position or not self.entry_price:
            return False
        
        if self.position == "long":
            profit_pct = (current_price - self.entry_price) / self.entry_price
            return profit_pct >= self.take_profit_pct
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
            return profit_pct >= self.take_profit_pct
    
    def check_trailing_stop(self, current_price: float, peak_price: float) -> bool:
        if not self.position:
            return False
        
        if self.position == "long":
            profit_pct = (current_price - self.entry_price) / self.entry_price
            trailing_trigger = (peak_price - current_price) / peak_price
            return profit_pct >= 0.02 and trailing_trigger >= self.trailing_stop_pct
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
            trailing_trigger = (current_price - peak_price) / peak_price
            return profit_pct >= 0.02 and trailing_trigger >= self.trailing_stop_pct
    
    def check_time_exit(self) -> bool:
        if not self.entry_time:
            return False
        
        hours_held = (datetime.now() - self.entry_time).total_seconds() / 3600
        return hours_held >= 2
    
    def run(self):
        signal = self.get_signal()
        ticker = self.client.get_ticker(self.inst_id)
        
        if ticker.get("code") != "0":
            print(f"获取价格失败: {ticker.get('msg')}")
            return
        
        current_price = float(ticker["data"][0]["last"])
        print(f"[{datetime.now().strftime('%H:%M:%S')}] DOGE: ${current_price:.5f} Signal: {signal}")
        
        if self.position:
            print(f"  持仓: {self.position} @ ${self.entry_price:.5f}")
            
            if self.check_stop_loss(current_price):
                print(f"  止损退出!")
                self.position = None
            elif self.check_take_profit(current_price):
                print(f"  止盈退出!")
                self.position = None
            elif self.check_time_exit():
                print(f"  时间到期退出!")
                self.position = None
        else:
            if signal == "long":
                print(f"  入场: LONG")
            elif signal == "short":
                print(f"  入场: SHORT")


def main():
    os.environ['OKX_API_KEY'] = '7c1d51b0-0104-476c-90db-c6dff1f0b090'
    os.environ['OKX_API_SECRET'] = 'AF8EB679F8AA4CE9A38C5069CB0737A7'
    os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'
    
    strategy = MACDStrategy(flag="1")
    strategy.run()


if __name__ == "__main__":
    main()
