"""回测"""

import os
import sys
from typing import List, Dict, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from okx_client import OKXTrader
from okx_client.utils import calculate_ema


class Position:
    def __init__(self, side: str, entry_price: float, entry_time: datetime,
                 key_candle: Dict, atr_at_entry: float):
        self.side: str = side
        self.entry_price: float = entry_price
        self.entry_time: datetime = entry_time
        self.key_candle: Dict = key_candle
        self.atr_at_entry: float = atr_at_entry
        
        self.first_take_profit_done: bool = False
        self.second_take_profit_done: bool = False
        self.breakeven_stop_moved: bool = False
        self.first_exit_price: Optional[float] = None
        self.first_exit_time: Optional[datetime] = None


class BacktestResult:
    def __init__(self):
        self.trades: List[Dict] = []
        self.initial_balance: float = 10000
        self.final_balance: float = 0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        
    def add_trade(self, entry_price: float, exit_price: float, side: str, pnl_pct: float):
        self.trades.append({
            'entry': entry_price,
            'exit': exit_price,
            'side': side,
            'pnl_pct': pnl_pct
        })
        if pnl_pct > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
    
    def calculate(self):
        self.total_trades = len(self.trades)
        if self.total_trades > 0:
            total_pnl_pct = sum(t['pnl_pct'] for t in self.trades)
            self.final_balance = self.initial_balance * (1 + total_pnl_pct / 100)
        else:
            self.final_balance = self.initial_balance
    
    def summary(self) -> Dict:
        win_rate = self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0
        avg_win = sum(t['pnl_pct'] for t in self.trades if t['pnl_pct'] > 0) / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = sum(t['pnl_pct'] for t in self.trades if t['pnl_pct'] < 0) / self.losing_trades if self.losing_trades > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.final_balance,
            'total_return': (self.final_balance - self.initial_balance) / self.initial_balance * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }


class MACDBacktest:
    def __init__(self, flag: str = "1"):
        self.client = OKXTrader(flag)
        self.inst_id = "DOGE-USDT"
        
        # 半木夏策略参数
        self.fast = 13
        self.slow = 34
        self.signal = 9
        
        self.debug = False
        
        self.stop_loss_pct = 0.018
        self.take_profit_pct = 0.018 * 1.5
        self.trailing_stop_pct = 0.015
        self.max_hours = 2
        
        self.result = BacktestResult()
    
    def check_trend_filter(self, current_price: float, closes: List[float]) -> str:
        ema200 = calculate_ema(closes, 200)
        if ema200 is None:
            return 'hold'
        
        if current_price > ema200:
            return 'long'
        elif current_price < ema200:
            return 'short'
        return 'hold'
    
    def calculate_atr(self, ohlc_list: List[Dict], period: int = 14) -> Optional[float]:
        """计算ATR"""
        if len(ohlc_list) < period + 1:
            return None
        
        tr_values = []
        for i in range(1, len(ohlc_list)):
            high = ohlc_list[i]['high']
            low = ohlc_list[i]['low']
            prev_close = ohlc_list[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_values.append(tr)
        
        if len(tr_values) < period:
            return None
        
        atr = sum(tr_values[-period:]) / period
        return atr
    
    def check_first_take_profit(self, position: Position, current_price: float) -> bool:
        if position.first_take_profit_done:
            return False
        
        if position.side == 'long':
            profit_pct = (current_price - position.entry_price) / position.entry_price
        else:
            profit_pct = (position.entry_price - current_price) / position.entry_price
        
        return profit_pct >= self.take_profit_pct
    
    def check_second_take_profit(self, position: Position, histogram_prev: float, histogram_curr: float) -> bool:
        if position.second_take_profit_done:
            return False
        
        if position.side == 'long':
            return histogram_prev < 0 and histogram_curr >= 0
        else:
            return histogram_prev > 0 and histogram_curr <= 0
    
    def get_breakeven_stop_price(self, position: Position) -> float:
        return position.entry_price
    
    def check_breakeven_stop(self, position: Position, current_price: float) -> bool:
        if not position.first_take_profit_done or position.breakeven_stop_moved:
            return False
        
        if position.side == 'long':
            return current_price <= position.entry_price
        else:
            return current_price >= position.entry_price
    
    def calculate_macd(self, closes: List[float]) -> Dict:
        if len(closes) < self.slow + self.signal:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'histogram_prev': 0}
        
        fast_ema = calculate_ema(closes, self.fast)
        slow_ema = calculate_ema(closes, self.slow)
        
        if fast_ema is None or slow_ema is None:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'histogram_prev': 0}
        
        macd_line = fast_ema - slow_ema
        
        macd_values = []
        for i in range(len(closes) - self.signal + 1):
            f = calculate_ema(closes[i:i+self.fast], self.fast)
            s = calculate_ema(closes[i:i+self.slow], self.slow)
            if f and s:
                macd_values.append(f - s)
        
        if len(macd_values) < self.signal:
            return {'macd': macd_line, 'signal': 0, 'histogram': macd_line, 'histogram_prev': 0}
        
        signal_line = calculate_ema(macd_values, self.signal)
        histogram = macd_line - signal_line if signal_line else 0
        
        # 获取前一个histogram
        histogram_prev = 0
        if len(macd_values) >= self.signal + 1:
            prev_macd = macd_values[-2]
            prev_signal = calculate_ema(macd_values[-self.signal-1:-1], self.signal) if len(macd_values) >= self.signal + 1 else 0
            histogram_prev = prev_macd - prev_signal if prev_signal else 0
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram,
            'histogram_prev': histogram_prev
        }
    
    def find_histogram_peaks(self, histograms: List[float], threshold: float = 0) -> List[int]:
        """找到histogram的波峰位置"""
        peaks = []
        for i in range(1, len(histograms) - 1):
            if histograms[i] > threshold:
                # 寻找波峰
                if histograms[i] > histograms[i-1] and histograms[i] > histograms[i+1]:
                    peaks.append(i)
        return peaks
    
    def detect_continuous_divergence(self, histograms: List[float], signal_type: str, min_gap_pct: float = 0.15) -> bool:
        if len(histograms) < 10:
            return False
        
        peaks = []
        for i in range(1, len(histograms) - 1):
            if signal_type == 'long':
                if histograms[i] < 0 and histograms[i] > histograms[i-1] and histograms[i] > histograms[i+1]:
                    peaks.append((i, histograms[i]))
            else:
                if histograms[i] > 0 and histograms[i] < histograms[i-1] and histograms[i] < histograms[i+1]:
                    peaks.append((i, histograms[i]))
        
        if len(peaks) < 2:
            return False
        
        for j in range(len(peaks) - 1):
            idx1, peak1 = peaks[j]
            idx2, peak2 = peaks[j + 1]
            
            if signal_type == 'long':
                if peak2 <= peak1:
                    return False
                gap = (peak2 - peak1) / abs(peak1)
                if gap < min_gap_pct:
                    return False
            else:
                if peak2 >= peak1:
                    return False
                gap = (peak1 - peak2) / peak1
                if gap < min_gap_pct:
                    return False
        
        return True
    
    def detect_divergence_and_key(self, ohlc: List[Dict], histogram: List[float]) -> tuple:
        if len(ohlc) < 30 or len(histogram) < 30:
            return 'hold', None
        
        recent_ohlc = ohlc[-30:]
        recent_hist = histogram[-30:]
        
        key_candle_idx = None
        signal_type = None
        
        for i in range(1, len(recent_hist)):
            if recent_hist[i-1] < 0 and recent_hist[i] >= 0:
                key_candle_idx = i
                signal_type = 'long'
                break
            elif recent_hist[i-1] > 0 and recent_hist[i] <= 0:
                key_candle_idx = i
                signal_type = 'short'
                break
        
        if key_candle_idx is None:
            if self.debug:
                print("DEBUG: 未找到关键K线（MACD颜色未反转）")
            return 'hold', None
        
        if key_candle_idx < 10:
            if self.debug:
                print(f"DEBUG: 关键K线位置太靠前: {key_candle_idx}")
            return 'hold', None
        
        if self.debug:
            print(f"DEBUG: 找到关键K线 idx={key_candle_idx} type={signal_type}")
        
        lookback = min(key_candle_idx, 15)
        div_ohlc = recent_ohlc[:key_candle_idx]
        div_hist = recent_hist[:key_candle_idx]
        
        if signal_type == 'long':
            price_lows = []
            for i in range(1, len(div_ohlc) - 1):
                if div_ohlc[i]['low'] < div_ohlc[i-1]['low'] and div_ohlc[i]['low'] < div_ohlc[i+1]['low']:
                    price_lows.append(div_ohlc[i]['low'])
            
            hist_lows = []
            for i in range(1, len(div_hist) - 1):
                if div_hist[i] < div_hist[i-1] and div_hist[i] < div_hist[i+1]:
                    if div_hist[i] < 0:
                        hist_lows.append(div_hist[i])
            
            if len(price_lows) >= 1 and len(hist_lows) >= 1:
                if self.debug:
                    print(f"DEBUG: 底背离 - 价格新低: {price_lows[-1]:.5f}, MACD红柱: {hist_lows[-1]:.6f}")
                key_candle = recent_ohlc[key_candle_idx]
                return 'long', key_candle
        
        elif signal_type == 'short':
            price_highs = []
            for i in range(1, len(div_ohlc) - 1):
                if div_ohlc[i]['high'] > div_ohlc[i-1]['high'] and div_ohlc[i]['high'] > div_ohlc[i+1]['high']:
                    price_highs.append(div_ohlc[i]['high'])
            
            hist_highs = []
            for i in range(1, len(div_hist) - 1):
                if div_hist[i] > div_hist[i-1] and div_hist[i] > div_hist[i+1]:
                    if div_hist[i] > 0:
                        hist_highs.append(div_hist[i])
            
            if len(price_highs) >= 1 and len(hist_highs) >= 1:
                if self.debug:
                    print(f"DEBUG: 顶背离 - 价格新高: {price_highs[-1]:.5f}, MACD绿柱: {hist_highs[-1]:.6f}")
                key_candle = recent_ohlc[key_candle_idx]
                return 'short', key_candle
        
        return 'hold', None
    
    def find_key_candle(self, ohlc: List[Dict], histogram: List[float], signal_type: str) -> Optional[Dict]:
        """找到关键K线：MACD深色柱子转浅色的第一根K线
        
        对于做多(底背离)：找到红柱转绿柱的那根K线
        对于做空(顶背离)：找到绿柱转红柱的那根K线
        """
        if len(ohlc) < 2 or len(histogram) < 2:
            return None
        
        for i in range(1, len(histogram)):
            if signal_type == 'long':
                # 红柱转绿柱 (负转正)
                if histogram[i-1] < 0 and histogram[i] >= 0:
                    return ohlc[i]
            elif signal_type == 'short':
                # 绿柱转红柱 (正转负)
                if histogram[i-1] > 0 and histogram[i] <= 0:
                    return ohlc[i]
        
        return None
    
    def run(self, days: int = 90, bar: str = "5m") -> BacktestResult:
        ts_start = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_ohlc = []
        
        first_batch = self.client.get_history_kline(self.inst_id, bar=bar, limit=300, after=str(ts_start))
        if first_batch.get('code') != '0' or not first_batch.get('data'):
            print(f"获取数据失败: {first_batch.get('msg')}")
            return self.result
        
        all_ohlc = [
            {
                'time': int(c[0]),
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4])
            }
            for c in first_batch['data']
        ]
        
        if len(all_ohlc) >= 300:
            last_ts = all_ohlc[-1]['time']
            second_batch = self.client.get_history_kline(self.inst_id, bar=bar, limit=300, after=str(last_ts))
            if second_batch.get('code') == '0' and second_batch.get('data'):
                more_ohlc = [
                    {
                        'time': int(c[0]),
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4])
                    }
                    for c in second_batch['data']
                ]
                all_ohlc.extend(more_ohlc)
        
        all_ohlc.sort(key=lambda x: x['time'])
        
        ohlc = all_ohlc
        
        print(f"回测数据: {len(ohlc)} 条 K线")
        
        position_obj = None
        
        all_histograms = []
        for i in range(len(ohlc)):
            closes = [c['close'] for c in ohlc[:i+1]]
            macd = self.calculate_macd(closes)
            all_histograms.append(macd['histogram'])
        
        all_histogram_prev = []
        for i in range(len(ohlc)):
            if i == 0:
                all_histogram_prev.append(0)
            else:
                all_histogram_prev.append(all_histograms[i-1])
        
        for i in range(self.slow + self.signal + 10, len(ohlc)):
            current_ohlc = ohlc[:i+1]
            closes = [c['close'] for c in current_ohlc]
            histograms = all_histograms[:i+1]
            histogram_prev = all_histogram_prev[i]
            
            signal_type, key_candle = self.detect_divergence_and_key(current_ohlc, histograms)
            current_price = ohlc[i]['close']
            current_time = datetime.fromtimestamp(ohlc[i]['time'] / 1000)
            trend = self.check_trend_filter(current_price, closes)
            
            if position_obj is None:
                if signal_type in ('long', 'short'):
                    if key_candle:
                        # 趋势过滤: Long必须Long趋势, Short必须Short趋势
                        if (signal_type == 'long' and trend == 'long') or \
                           (signal_type == 'short' and trend == 'short'):
                            atr_val = self.calculate_atr(current_ohlc, 13) or 0
                            position_obj = Position(
                                side=signal_type,
                                entry_price=current_price,
                                entry_time=current_time,
                                key_candle=key_candle,
                                atr_at_entry=atr_val
                            )
                            print(f"[{current_time}] 入场 {signal_type.upper()} (背离+趋势) @ {current_price:.5f}")
            else:
                hours_held = (current_time - position_obj.entry_time).total_seconds() / 3600
                exit_triggered = False
                exit_reason = ""
                exit_price = current_price
                exit_partial = False
                
                if position_obj.side == 'long':
                    loss_pct = (position_obj.entry_price - current_price) / position_obj.entry_price
                    profit_pct = (current_price - position_obj.entry_price) / position_obj.entry_price
                    
                    if not position_obj.breakeven_stop_moved:
                        stop_price = position_obj.key_candle['low'] - position_obj.atr_at_entry
                        if current_price <= stop_price:
                            exit_triggered = True
                            exit_reason = "止损"
                    else:
                        if current_price <= position_obj.entry_price:
                            exit_triggered = True
                            exit_reason = "盈亏平衡止损"
                    
                    if not exit_triggered and not position_obj.first_take_profit_done:
                        if self.check_first_take_profit(position_obj, current_price):
                            position_obj.first_take_profit_done = True
                            position_obj.first_exit_price = current_price
                            position_obj.first_exit_time = current_time
                            position_obj.breakeven_stop_moved = True
                            exit_triggered = True
                            exit_reason = "50%仓位止盈(1:1.5)"
                            exit_partial = True
                    
                    if not exit_triggered and not position_obj.second_take_profit_done:
                        if self.check_second_take_profit(position_obj, histogram_prev, histograms[-1]):
                            position_obj.second_take_profit_done = True
                            exit_triggered = True
                            exit_reason = "50%仓位右侧止盈(MACD反转)"
                    
                    if not exit_triggered and hours_held >= self.max_hours:
                        exit_triggered = True
                        exit_reason = "时间到期"
                        
                else:
                    loss_pct = (current_price - position_obj.entry_price) / position_obj.entry_price
                    profit_pct = (position_obj.entry_price - current_price) / position_obj.entry_price
                    
                    if not position_obj.breakeven_stop_moved:
                        stop_price = position_obj.key_candle['high'] + position_obj.atr_at_entry
                        if current_price >= stop_price:
                            exit_triggered = True
                            exit_reason = "止损"
                    else:
                        if current_price >= position_obj.entry_price:
                            exit_triggered = True
                            exit_reason = "盈亏平衡止损"
                    
                    if not exit_triggered and not position_obj.first_take_profit_done:
                        if self.check_first_take_profit(position_obj, current_price):
                            position_obj.first_take_profit_done = True
                            position_obj.first_exit_price = current_price
                            position_obj.first_exit_time = current_time
                            position_obj.breakeven_stop_moved = True
                            exit_triggered = True
                            exit_reason = "50%仓位止盈(1:1.5)"
                            exit_partial = True
                    
                    if not exit_triggered and not position_obj.second_take_profit_done:
                        if self.check_second_take_profit(position_obj, histogram_prev, histograms[-1]):
                            position_obj.second_take_profit_done = True
                            exit_triggered = True
                            exit_reason = "50%仓位右侧止盈(MACD反转)"
                    
                    if not exit_triggered and hours_held >= self.max_hours:
                        exit_triggered = True
                        exit_reason = "时间到期"
                
                if exit_triggered:
                    if exit_partial and position_obj.first_exit_price is not None:
                        if position_obj.side == 'long':
                            pnl_pct = (position_obj.first_exit_price - position_obj.entry_price) / position_obj.entry_price * 100
                        else:
                            pnl_pct = (position_obj.entry_price - position_obj.first_exit_price) / position_obj.entry_price * 100
                    else:
                        if position_obj.side == 'long':
                            pnl_pct = (current_price - position_obj.entry_price) / position_obj.entry_price * 100
                        else:
                            pnl_pct = (position_obj.entry_price - current_price) / position_obj.entry_price * 100
                    
                    print(f"[{current_time}] {exit_reason} @ {exit_price:.5f} ({pnl_pct:+.2f}%)")
                    
                    if exit_partial:
                        if position_obj.side == 'long':
                            position_obj.entry_price = current_price
                        else:
                            position_obj.entry_price = current_price
                        position_obj.first_take_profit_done = False
                        position_obj.breakeven_stop_moved = False
                    else:
                        self.result.add_trade(position_obj.entry_price, exit_price, position_obj.side, pnl_pct)
                        position_obj = None
        
        self.result.calculate()
        return self.result


def main():
    os.environ['OKX_API_KEY'] = '80ef8950-4469-4509-9c82-b226c0bc991c'
    os.environ['OKX_API_SECRET'] = '0E806F692183A46059817C59A59491F0'
    os.environ['OKX_PASSPHRASE'] = 'AbcD@1234'
    
    bt = MACDBacktest(flag="0")
    result = bt.run(days=90, bar="5m")
    
    print("\n" + "="*50)
    print("回测结果")
    print("="*50)
    s = result.summary()
    print(f"初始资金: ${s['initial_balance']:.2f}")
    print(f"最终资金: ${s['final_balance']:.2f}")
    print(f"总收益: {s['total_return']:+.2f}%")
    print(f"交易次数: {s['total_trades']}")
    print(f"胜率: {s['win_rate']:.2f}%")
    print(f"盈利因子: {s['profit_factor']:.2f}")


if __name__ == "__main__":
    main()
