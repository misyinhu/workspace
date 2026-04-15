# 半木夏 MACD 背离策略增强实现计划

## Discovery

### Original Request (from User)
完善 backtest.py，实现完整的半木夏策略，包含：
1. 更严格的连续背离检测（30%阈值）
2. 右侧止盈逻辑（50%仓位持有到MACD反转）
3. 止盈后移动止损到盈亏平衡点

### Interview Summary
- **Point 1**: MACD参数 13,34,9 - 已有基础实现
- **Point 2**: 背离检测使用关键K线逻辑 - 已有基础但缺少连续背离判断
- **Point 3**: 止损使用关键K线低点/高点 - ATR(13) - 已实现
- **Point 4**: 止盈分两部分：50%仓位1:1.5止盈 + 50%仓位右侧止盈 - 需新增
- **Point 5**: 2小时时间限制 - 已实现
- **Point 6**: 连续背离需30%波峰高度差 - 需新增
- **Point 7**: 止盈后移动止损到盈亏平衡点 - 需新增

### Research Findings
- `backtest.py:161-222`: detect_divergence_and_key() - 现有背离检测，检测价格 lows 和 histogram lows
- `backtest.py:224-243`: find_key_candle() - 找关键K线逻辑正确
- `backtest.py:329-365`: 现有止盈逻辑只有固定1:1.5止盈，缺少右侧止盈

---

## Non-Goals (What we're NOT building)
- 不实现实盘交易，只做回测增强
- 不改变MACD参数（保持13,34,9）
- 不实现仓位管理（固定100%仓位）

---

## Task Overview

| Task | Description | Dependencies |
|------|-------------|--------------|
| 1 | 添加连续背离检测（30%阈值） | none |
| 2 | 添加波峰波谷数据结构 | none |
| 3 | 添加ATR计算（13周期）已存在但需验证 | none |
| 4 | 重构入场条件检测逻辑 | 1, 2 |
| 5 | 实现分仓止盈逻辑（50%固定 + 50%右侧） | 4 |
| 6 | 实现止盈后移动止损到盈亏平衡点 | 5 |
| 7 | 编写单元测试 | 1-6 |
| 8 | 运行回测验证 | 7 |

---

## Tasks

### 1. 添加连续背离检测（30%阈值）函数

**Depends on**: none

**Files:**
- Modify: `okx_client/backtest.py:151-159`

**What to do**:
- Step 1: Write failing test first
  ```python
  def test_continuous_divergence_30_percent_threshold():
      """测试连续背离30%阈值检测"""
      bt = MACDBacktest()
      
      # 模拟场景：波峰高度差小于30%
      histograms = [0, -1, -2, -3, -2, -1, -2, -3, -4, -3, -2]
      # 波峰: -1, -2, -4 (应该检测到不满足30%差)
      
      result = bt.detect_continuous_divergence(histograms, 'long')
      assert result == False  # 应该不通过
      
      # 模拟场景：波峰高度差大于30%
      histograms2 = [0, -1, -2, -10, -5, -2, -15, -8, -3]
      # 波峰: -1, -10, -15 (差值>30%)
      result2 = bt.detect_continuous_divergence(histograms2, 'long')
      assert result2 == True  # 应该通过
  ```
- Step 2: 运行测试验证失败
  ```bash
  cd /Users/wang/.opencode/workspace/trading && python3 -m pytest okx_client/test_backtest.py::test_continuous_divergence_30_percent_threshold -v
  ```
  预期: FAIL (函数不存在)

- Step 3: 添加实现
  ```python
  def detect_continuous_divergence(self, histograms: List[float], signal_type: str, min_gap_pct: float = 0.30) -> bool:
      """检测连续背离：波峰高度差30%以上
      
      Args:
          histograms: MACD histogram列表
          signal_type: 'long' 或 'short'
          min_gap_pct: 相邻波峰最小差值百分比，默认30%
      
      Returns:
          是否满足连续背离条件
      """
      if len(histograms) < 10:
          return False
      
      # 找波峰
      peaks = []
      for i in range(1, len(histograms) - 1):
          if signal_type == 'long':
              # 做多：找红柱波峰（负值向上找，即绝对值变小）
              if histograms[i] < 0 and histograms[i] > histograms[i-1] and histograms[i] > histograms[i+1]:
                  peaks.append(histograms[i])
          else:
              # 做空：找绿柱波峰（正值向下找，即绝对值变小）
              if histograms[i] > 0 and histograms[i] < histograms[i-1] and histograms[i] < histograms[i+1]:
                  peaks.append(histograms[i])
      
      if len(peaks) < 2:
          return False
      
      # 检查相邻波峰高度差是否>30%
      for j in range(len(peaks) - 1):
          prev_peak = peaks[j]
          curr_peak = peaks[j + 1]
          
          if signal_type == 'long':
              # 红柱：找波峰创新高（负值绝对值变小，即数值变大）
              # 例如: -10 -> -5 表示从深度红柱变为浅红柱
              if curr_peak <= prev_peak:  # 没有创新高
                  return False
              gap = (curr_peak - prev_peak) / abs(prev_peak)
              if gap < min_gap_pct:
                  return False
          else:
              # 绿柱：找波峰创新低（正值绝对值变小，即数值变小）
              if curr_peak >= prev_peak:  # 没有创新低
                  return False
              gap = (prev_peak - curr_peak) / prev_peak
              if gap < min_gap_pct:
                  return False
      
      return True
  ```

- Step 4: 运行测试验证通过
  ```bash
  cd /Users/wang/.opencode/workspace/trading && python3 -m pytest okx_client/test_backtest.py::test_continuous_divergence_30_percent_threshold -v
  ```
  预期: PASS

- Step 5: 提交
  ```bash
  cd /Users/wang/.opencode/workspace/trading && git add okx_client/backtest.py okx_client/test_backtest.py && git commit -m "feat: add 30% threshold continuous divergence detection"
  ```

**Must NOT do**:
- 不修改现有检测逻辑，只是新增函数

**References**:
- `backtest.py:161-222` - 现有detect_divergence_and_key逻辑

**Verify**:
- [ ] Run: `python3 -m pytest okx_client/test_backtest.py::test_continuous_divergence_30_percent_threshold -v` → PASS

---

### 2. 添加波峰波谷数据结构

**Depends on**: none

**Files:**
- Modify: `okx_client/backtest.py:12-57` (BacktestResult class area)

**What to do**:
- Step 1: 添加持仓状态类
  ```python
  class Position:
      def __init__(self, side: str, entry_price: float, entry_time: datetime, 
                   key_candle: Dict, atr_at_entry: float):
          self.side = side  # 'long' or 'short'
          self.entry_price = entry_price
          self.entry_time = entry_time
          self.key_candle = key_candle  # 关键K线
          self.atr_at_entry = atr_at_entry
          
          # 分仓止盈相关
          self.first_take_profit_done = False  # 50%仓位1:1.5已完成
          self.second_take_profit_done = False  # 50%仓位右侧止盈已完成
          self.breakeven_stop_moved = False  # 是否已移动止损到盈亏平衡
          self.first_exit_price = None  # 第一次止盈价格
          self.first_exit_time = None  # 第一次止盈时间
  ```

- Step 2: 运行语法检查
  ```bash
  cd /Users/wang/.opencode/workspace/trading && python3 -m py_compile okx_client/backtest.py
  ```

- Step 3: 提交
  ```bash
  cd /Users/wang/.opencode/workspace/trading && git add okx_client/backtest.py && git commit -m "feat: add Position class for split take profit tracking"
  ```

**Must NOT do**:
- 不改变现有交易逻辑

**References**:
- `backtest.py:288-376` - 现有持仓管理逻辑

**Verify**:
- [ ] Run: `python3 -m py_compile okx_client/backtest.py` → 无错误

---

### 3. 实现 ATR 计算验证

**Depends on**: none

**Files:**
- Test: `okx_client/test_backtest.py` (新建)
- Reference: `backtest.py:88-110`

**What to do**:
- Step 1: 写测试
  ```python
  def test_calculate_atr():
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
      assert atr is not None
      assert atr > 0
  ```

- Step 2: 运行测试
  ```bash
  cd /Users/wang/.opencode/workspace/trading && python3 -m pytest okx_client/test_backtest.py::test_calculate_atr -v
  ```
  预期: PASS (ATR已存在)

- Step 3: 提交
  ```bash
  cd /Users/wang/.opencode/workspace/trading && git add okx_client/test_backtest.py && git commit -m "test: add ATR calculation verification test"
  ```

**References**:
- `backtest.py:88-110` - 现有calculate_atr实现

**Verify**:
- [ ] Run: `python3 -m pytest okx_client/test_backtest.py::test_calculate_atr -v` → PASS

---

### 4. 重构入场条件检测逻辑

**Depends on**: 1, 2

**Files:**
- Modify: `backtest.py:301-320`

**What to do**:
- Step 1: 写失败的测试
  ```python
  def test_entry_with_continuous_divergence():
      """测试入场需要满足连续背离30%阈值"""
      bt = MACDBacktest()
      
      # 构造数据：背离但波峰差<30%
      # 应该不入场
  ```

- Step 2: 修改detect_divergence_and_key函数，整合连续背离检测

- Step 3: 运行测试验证

- Step 4: 提交

**Must NOT do**:
- 不改变其他逻辑，只改入场条件

**Verify**:
- [ ] Backtest runs without errors

---

### 5. 实现分仓止盈逻辑（50%固定 + 50%右侧）

**Depends on**: 4

**Files:**
- Modify: `backtest.py:336-365`

**What to do**:
- Step 1: 写测试
  ```python
  def test_split_take_profit_logic():
      """测试分仓止盈：50%仓位1:1.5 + 50%仓位右侧"""
      bt = MACDBacktest()
      position = Position('long', entry_price=100, entry_time=datetime.now(),
                         key_candle={'low': 99}, atr_at_entry=1)
      
      # 场景1：价格到达1:1.5止盈点
      current_price = 100 + 100 * 0.018 * 1.5  # 102.7
      should_exit_50pct = bt.check_first_take_profit(position, current_price)
      assert should_exit_50pct == True
      
      # 场景2：MACD颜色反转（右侧止盈）
      position.first_take_profit_done = True
      # 假设MACD从红转绿
      should_exit_remain = bt.check_second_take_profit(position, histogram_prev=-1, histogram_curr=1)
      assert should_exit_remain == True
  ```

- Step 2: 添加检查函数
  ```python
  def check_first_take_profit(self, position: Position, current_price: float) -> bool:
      """检查是否触发50%仓位1:1.5止盈"""
      if position.first_take_profit_done:
          return False
      
      if position.side == 'long':
          profit_pct = (current_price - position.entry_price) / position.entry_price
      else:
          profit_pct = (position.entry_price - current_price) / position.entry_price
      
      return profit_pct >= self.take_profit_pct  # 0.018 * 1.5
  
  def check_second_take_profit(self, position: Position, histogram_prev: float, histogram_curr: float) -> bool:
      """检查是否触发右侧止盈（MACD颜色反转）"""
      if position.second_take_profit_done:
          return False
      
      if position.side == 'long':
          # 多单：MACD从红柱变绿柱（负转正）
          return histogram_prev < 0 and histogram_curr >= 0
      else:
          # 空单：MACD从绿柱变红柱（正转负）
          return histogram_prev > 0 and histogram_curr <= 0
  ```

- Step 3: 修改主循环的止盈逻辑

- Step 4: 提交

**Must NOT do**:
- 不改变止损逻辑

**Verify**:
- [ ] Run: `python3 -m pytest okx_client/test_backtest.py::test_split_take_profit_logic -v` → PASS

---

### 6. 实现止盈后移动止损到盈亏平衡点

**Depends on**: 5

**Files:**
- Modify: `backtest.py:336-365`

**What to do**:
- Step 1: 写测试
  ```python
  def test_move_stop_to_breakeven():
      """测试止盈后移动止损到盈亏平衡点"""
      bt = MACDBacktest()
      position = Position('long', entry_price=100, entry_time=datetime.now(),
                         key_candle={'low': 99}, atr_at_entry=1)
      position.first_take_profit_done = True
      position.first_exit_price = 102.7  # 1:1.5止盈点
      position.breakeven_stop_moved = False
      
      # 检查移动止损
      stop_price = bt.get_breakeven_stop_price(position)
      assert stop_price == position.entry_price  # 应该移动到入场价
      
      # 验证：当价格回到入场价时触发止损
      current_price = 100
      should_stop = bt.check_breakeven_stop(position, current_price)
      assert should_stop == True
  ```

- Step 2: 添加函数
  ```python
  def get_breakeven_stop_price(self, position: Position) -> float:
      """获取盈亏平衡点止损价格"""
      if position.side == 'long':
          return position.entry_price
      else:
          return position.entry_price
  
  def check_breakeven_stop(self, position: Position, current_price: float) -> bool:
      """检查是否触发盈亏平衡止损"""
      if not position.first_take_profit_done or position.breakeven_stop_moved:
          return False
      
      if position.side == 'long':
          return current_price <= position.entry_price
      else:
          return current_price >= position.entry_price
  ```

- Step 3: 修改主循环，在第一次止盈后更新止损

- Step 4: 提交

**Must NOT do**:
- 不改变原有的固定止损逻辑

**Verify**:
- [ ] Run: `python3 -m pytest okx_client/test_backtest.py::test_move_stop_to_breakeven -v` → PASS

---

### 7. 编写完整单元测试

**Depends on**: 1-6

**Files:**
- Create: `okx_client/test_backtest.py`

**What to do**:
- Step 1: 创建测试文件，包含所有测试用例
- Step 2: 运行完整测试套件
  ```bash
  cd /Users/wang/.opencode/workspace/trading && python3 -m pytest okx_client/test_backtest.py -v
  ```
- Step 3: 提交

**Verify**:
- [ ] All tests pass

---

### 8. 运行回测验证

**Depends on**: 7

**Files:**
- Run: `okx_client/backtest.py`

**What to do**:
- Step 1: 运行回测
  ```bash
  cd /Users/wang/.opencode/workspace/trading && python3 okx_client/backtest.py
  ```
- Step 2: 检查输出包含新的止盈逻辑（日志显示"第一次止盈"、"右侧止盈"等）
- Step 3: 提交

**Verify**:
- [ ] 回测成功运行，无错误
- [ ] 输出显示分仓止盈逻辑

---

## Execution Options

Two approaches available:

1. **Subagent-Driven (This Session)** - I dispatch fresh subagent per task, review between tasks, fast iteration
2. **Parallel Session (Separate)** - Open new session with executing-plans skill, batch execution with checkpoints

Which approach would you prefer?