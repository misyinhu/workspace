"""半木夏 MACD 背离策略测试"""

import os
import sys
from datetime import datetime
from typing import Dict

os.environ.setdefault('OKX_API_KEY', 'test')
os.environ.setdefault('OKX_API_SECRET', 'test')
os.environ.setdefault('OKX_PASSPHRASE', 'test')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试前需要导入 backtest 模块中的类
# 先确保 backtest.py 已更新


def test_continuous_divergence_30_percent_threshold():
    from okx_client.backtest import MACDBacktest
    
    bt = MACDBacktest()
    
    histograms1 = [0, -1, -2, -3, -2, -1, -2, -3, -4, -3, -2]
    result1 = bt.detect_continuous_divergence(histograms1, 'long')
    assert result1 == False
    
    histograms4 = [0, -1, -10, -8, -5, -6, -4, -2, -6, -5, -3]
    result4 = bt.detect_continuous_divergence(histograms4, 'long')
    assert result4 == True
    
    histograms5 = [0, -1, -10, -9, -8, -7, -6, -5, -9, -8, -6]
    result5 = bt.detect_continuous_divergence(histograms5, 'long')
    assert result5 == False
    
    print("test_continuous_divergence_30_percent_threshold PASSED")


def test_calculate_atr():
    """测试 ATR 计算"""
    from okx_client.backtest import MACDBacktest
    
    bt = MACDBacktest()
    
    # 模拟OHLC数据
    ohlc = [
        {'high': 100, 'low': 98, 'close': 99},
        {'high': 101, 'low': 98, 'close': 100},
        {'high': 102, 'low': 99, 'close': 101},
        {'high': 103, 'low': 100, 'close': 102},
        {'high': 104, 'low': 101, 'close': 103},
        {'high': 105, 'low': 102, 'close': 104},
        {'high': 106, 'low': 103, 'close': 105},
        {'high': 107, 'low': 104, 'close': 106},
        {'high': 108, 'low': 105, 'close': 107},
        {'high': 109, 'low': 106, 'close': 108},
        {'high': 110, 'low': 107, 'close': 109},
        {'high': 111, 'low': 108, 'close': 110},
        {'high': 112, 'low': 109, 'close': 111},
        {'high': 113, 'low': 110, 'close': 112},
        {'high': 114, 'low': 111, 'close': 113},
    ]
    
    atr = bt.calculate_atr(ohlc, 13)
    assert atr is not None, "ATR should not be None"
    assert atr > 0, "ATR should be positive"
    
    print(f"ATR = {atr}")
    print("test_calculate_atr PASSED")


def test_position_class():
    """测试 Position 类"""
    from okx_client.backtest import Position
    
    key_candle = {'low': 99, 'high': 101}
    entry_time = datetime.now()
    
    pos = Position(
        side='long',
        entry_price=100.0,
        entry_time=entry_time,
        key_candle=key_candle,
        atr_at_entry=1.5
    )
    
    assert pos.side == 'long'
    assert pos.entry_price == 100.0
    assert pos.first_take_profit_done == False
    assert pos.second_take_profit_done == False
    assert pos.breakeven_stop_moved == False
    
    print("test_position_class PASSED")


def test_split_take_profit_logic():
    """测试分仓止盈逻辑"""
    from okx_client.backtest import MACDBacktest, Position
    
    bt = MACDBacktest()
    entry_time = datetime.now()
    
    position = Position(
        side='long',
        entry_price=100.0,
        entry_time=entry_time,
        key_candle={'low': 99},
        atr_at_entry=1.0
    )
    
    # 场景1：价格到达1:1.5止盈点 (0.018 * 1.5 = 0.027)
    # 100 * (1 + 0.027) = 102.7
    current_price = 102.7
    should_exit_50pct = bt.check_first_take_profit(position, current_price)
    assert should_exit_50pct == True, "1:1.5止盈点应该触发"
    
    # 场景2：未到达止盈点
    position2 = Position(
        side='long',
        entry_price=100.0,
        entry_time=entry_time,
        key_candle={'low': 99},
        atr_at_entry=1.0
    )
    current_price2 = 101.0  # 只有1%涨幅
    should_not_exit = bt.check_first_take_profit(position2, current_price2)
    assert should_not_exit == False, "未到止盈点不应该触发"
    
    print("test_split_take_profit_logic PASSED")


def test_second_take_profit():
    """测试右侧止盈（MACD反转）"""
    from okx_client.backtest import MACDBacktest, Position
    
    bt = MACDBacktest()
    entry_time = datetime.now()
    
    # 场景1：多单，MACD从红柱变绿柱（负转正）
    position = Position(
        side='long',
        entry_price=100.0,
        entry_time=entry_time,
        key_candle={'low': 99},
        atr_at_entry=1.0
    )
    position.first_take_profit_done = True  # 已完成第一次止盈
    
    should_exit = bt.check_second_take_profit(position, histogram_prev=-1, histogram_curr=1)
    assert should_exit == True, "MACD红转绿应该触发右侧止盈"
    
    # 场景2：多单，MACD仍在红柱区域
    position2 = Position(
        side='long',
        entry_price=100.0,
        entry_time=entry_time,
        key_candle={'low': 99},
        atr_at_entry=1.0
    )
    position2.first_take_profit_done = True
    
    should_not_exit = bt.check_second_take_profit(position2, histogram_prev=-2, histogram_curr=-1)
    assert should_not_exit == False, "MACD未反转不应该触发"
    
    print("test_second_take_profit PASSED")


def test_breakeven_stop():
    """测试盈亏平衡止损"""
    from okx_client.backtest import MACDBacktest, Position
    
    bt = MACDBacktest()
    entry_time = datetime.now()
    
    position = Position(
        side='long',
        entry_price=100.0,
        entry_time=entry_time,
        key_candle={'low': 99},
        atr_at_entry=1.0
    )
    position.first_take_profit_done = True
    position.first_exit_price = 102.7
    position.breakeven_stop_moved = False
    
    # 检查移动止损价格
    stop_price = bt.get_breakeven_stop_price(position)
    assert stop_price == position.entry_price, "止损应该移动到入场价"
    
    # 验证：当价格回到入场价时触发止损
    current_price = 100.0
    should_stop = bt.check_breakeven_stop(position, current_price)
    assert should_stop == True, "价格回到入场价应该触发止损"
    
    # 价格仍在止盈点以上，不应该触发
    current_price2 = 101.5
    should_not_stop = bt.check_breakeven_stop(position, current_price2)
    assert should_not_stop == False, "价格高于入场价不应触发"
    
    print("test_breakeven_stop PASSED")


if __name__ == "__main__":
    print("Running tests...")
    
    try:
        test_position_class()
    except ImportError as e:
        print(f"Position class not yet implemented: {e}")
    
    try:
        test_calculate_atr()
    except ImportError as e:
        print(f"ATR test failed: {e}")
    
    try:
        test_continuous_divergence_30_percent_threshold()
    except (ImportError, AttributeError) as e:
        print(f"Continuous divergence test failed: {e}")
    
    try:
        test_split_take_profit_logic()
    except (ImportError, AttributeError) as e:
        print(f"Split take profit test failed: {e}")
    
    try:
        test_second_take_profit()
    except (ImportError, AttributeError) as e:
        print(f"Second take profit test failed: {e}")
    
    try:
        test_breakeven_stop()
    except (ImportError, AttributeError) as e:
        print(f"Breakeven stop test failed: {e}")
    
    print("\nTests complete.")