# 双品种套利分析模式实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 resonance 页面增加双品种套利分析模式，支持价差/比率/相关性视图和 Z-Score 信号触发

**Architecture:** 
- 新增 `analysis.py` 中的套利计算函数（spread, ratio, correlation, zscore）
- 修改 `01_resonance.py` 侧边栏增加第二个品种选择器，新增双品种 Tab 视图
- 复用现有 quant-core API 获取两个品种数据

**Tech Stack:** Python, Streamlit, pandas, numpy, plotly (复用现有图表)

---

## 文件结构

| 文件 | 变更 |
|------|------|
| `kanban/src/analysis.py` | 新增套利计算函数 |
| `kanban/src/config.py` | 新增套利参数常量 |
| `kanban/pages/01_resonance.py` | 修改侧边栏、新增双品种视图 |
| `kanban/tests/test_spread_pairs.py` | 新增测试文件 |

---

## Task 1: 添加套利参数配置

**Files:**
- Modify: `kanban/src/config.py`

- [ ] **Step 1: 添加套利参数常量**

在 `config.py` 末尾添加：

```python
# 套利分析参数
ARBITRAGE_DEFAULTS = {
    "zscore_threshold": 3.0,           # Z-Score 触发阈值
    "correlation_threshold": 0.8,     # 相关性触发阈值
    "rsi_divergence_threshold": 20,    # RSI 背离阈值
    "correlation_window": 20,          # 滚动相关性窗口
}
```

---

## Task 2: 添加套利计算函数

**Files:**
- Modify: `kanban/src/analysis.py`

- [ ] **Step 1: 添加 calculate_spread 函数**

在 `analysis.py` 末尾添加：

```python
def calculate_spread(bars1: list, bars2: list) -> list:
    """计算价差序列"""
    if not bars1 or not bars2:
        return []
    closes1 = [b.get("close", 0) for b in bars1]
    closes2 = [b.get("close", 0) for b in bars2]
    min_len = min(len(closes1), len(closes2))
    return [closes1[i] - closes2[i] for i in range(min_len)]
```

- [ ] **Step 2: 添加 calculate_ratio 函数**

```python
def calculate_ratio(bars1: list, bars2: list) -> list:
    """计算比率序列"""
    if not bars1 or not bars2:
        return []
    closes1 = [b.get("close", 0) for b in bars1]
    closes2 = [b.get("close", 0) for b in bars2]
    min_len = min(len(closes1), len(closes2))
    return [closes1[i] / closes2[i] if closes2[i] != 0 else 0 for i in range(min_len)]
```

- [ ] **Step 3: 添加 calculate_correlation 函数**

```python
def calculate_correlation(bars1: list, bars2: list, window: int = 20) -> float:
    """计算皮尔逊相关系数"""
    if not bars1 or not bars2 or len(bars1) < window:
        return 0.0
    closes1 = np.array([b.get("close", 0) for b in bars1[-window:]])
    closes2 = np.array([b.get("close", 0) for b in bars2[-window:]])
    if np.std(closes1) == 0 or np.std(closes2) == 0:
        return 0.0
    return float(np.corrcoef(closes1, closes2)[0, 1])
```

- [ ] **Step 4: 添加 calculate_zscore 函数**

```python
def calculate_zscore(spread_series: list) -> dict:
    """计算 Z-Score"""
    if not spread_series or len(spread_series) < 2:
        return {"zscore": 0, "mean": 0, "std": 0}
    spread = np.array(spread_series)
    mean = float(np.mean(spread))
    std = float(np.std(spread))
    current = spread[-1]
    zscore = (current - mean) / std if std != 0 else 0
    return {"zscore": float(zscore), "mean": mean, "std": std}
```

- [ ] **Step 5: 添加 generate_arbitrage_signal 函数**

```python
def generate_arbitrage_signal(zscore: float, correlation: float, rsi1: float, rsi2: float) -> dict:
    """多条件组合信号生成"""
    from .config import ARBITRAGE_DEFAULTS
    zscore_threshold = ARBITRAGE_DEFAULTS["zscore_threshold"]
    corr_threshold = ARBITRAGE_DEFAULTS["correlation_threshold"]
    rsi_div_threshold = ARBITRAGE_DEFAULTS["rsi_divergence_threshold"]
    
    signals = []
    
    # 条件1: Z-Score > 3σ
    if abs(zscore) > zscore_threshold:
        signal_type = "ZSCORE_LONG" if zscore > 0 else "ZSCORE_SHORT"
        signals.append((signal_type, zscore))
    
    # 条件2: 相关性 > 0.8
    if correlation > corr_threshold:
        signals.append(("CORRELATION_OK", correlation))
    
    # 条件3: RSI 背离
    if abs(rsi1 - rsi2) > rsi_div_threshold:
        signals.append(("RSI_DIVERGE", abs(rsi1 - rsi2)))
    
    # 综合判断
    has_zscore_long = any(s[0] == "ZSCORE_LONG" for s in signals)
    has_zscore_short = any(s[0] == "ZSCODE_SHORT" for s in signals)
    has_corr = any(s[0] == "CORRELATION_OK" for s in signals)
    
    if has_zscore_long and has_corr:
        return {"signal": "SELL_SPREAD", "emoji": "📉", "reason": f"价差偏高 Z={zscore:.2f}, 相关性={correlation:.2f}"}
    elif has_zscore_short and has_corr:
        return {"signal": "BUY_SPREAD", "emoji": "📈", "reason": f"价差偏低 Z={zscore:.2f}, 相关性={correlation:.2f}"}
    
    return {"signal": "WATCH", "emoji": "➡️", "reason": "条件未触发"}
```

---

## Task 3: 修改 01_resonance.py 侧边栏

**Files:**
- Modify: `kanban/pages/01_resonance.py:48-64`

- [ ] **Step 1: 修改侧边栏添加第二个品种选择器**

将原来的第 48-64 行替换为：

```python
    # 跨品种套利
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 跨品种套利")
    enable_spread = st.sidebar.toggle("启用双品种模式", value=False, key="enable_spread")
    
    symbol2 = ""
    source2 = "tradingview"
    
    if enable_spread:
        st.sidebar.info("双品种模式已启用")
        
        # 品种2选择器
        if instruments:
            options2 = [f"{i['symbol']} - {i['name']}" for i in instruments]
            selected2 = st.sidebar.selectbox("品种 2", options2, index=1 if len(options2) > 1 else 0, key="instrument_select2")
            symbol2 = selected2.split(" - ")[0]
        else:
            symbol2 = st.sidebar.text_input("品种 2 代码", placeholder="如: ETH-USDT-SWAP", key="symbol2_input")
        
        if symbol2:
            source2 = get_source_for_symbol(symbol2)
```

---

## Task 4: 添加双品种视图 Tab

**Files:**
- Modify: `kanban/pages/01_resonance.py`

- [ ] **Step 1: 在 render_main_content 前添加双品种渲染函数**

在 `render_main_content` 函数之前添加：

```python
def render_pair_analysis(symbol1: str, symbol2: str, source1: str, source2: str):
    """渲染双品种套利分析"""
    from .data import fetch_pair_data
    from .analysis import calculate_spread, calculate_ratio, calculate_correlation, calculate_zscore, generate_arbitrage_signal
    
    st.markdown("### 🔗 双品种套利分析")
    
    # 获取双品种数据
    pair_data = fetch_pair_data(symbol1, symbol2)
    data1 = pair_data.get("data1", {}).get("timeframes", {})
    data2 = pair_data.get("data2", {}).get("timeframes", {})
    
    # 取日线数据计算
    bars1 = pair_data.get("bars1", [])
    bars2 = pair_data.get("bars2", [])
    
    if not bars1 or not bars2:
        st.warning("数据加载中...")
        return
    
    # 计算指标
    spread_data = calculate_spread(bars1, bars2)
    ratio_data = calculate_ratio(bars1, bars2)
    correlation = calculate_correlation(bars1, bars2)
    zscore_info = calculate_zscore(spread_data)
    zscore = zscore_info.get("zscore", 0)
    
    # 获取 RSI
    rsi1 = data1.get("1D", {}).get("rsi", 50)
    rsi2 = data2.get("1D", {}).get("rsi", 50)
    
    # 生成信号
    signal_info = generate_arbitrage_signal(zscore, correlation, rsi1, rsi2)
    
    # Tab 视图
    tab_spread, tab_ratio, tab_corr = st.tabs(["📊 价差视图", "📈 比率视图", "🔗 相关性视图"])
    
    with tab_spread:
        if spread_data:
            df_spread = pd.DataFrame({
                "日期": [f"Day {i+1}" for i in range(len(spread_data))],
                "价差": spread_data
            })
            st.line_chart(df_spread.set_index("日期"))
            st.caption(f"当前价差: {spread_data[-1]:.4f}")
        else:
            st.info("暂无价差数据")
    
    with tab_ratio:
        if ratio_data:
            df_ratio = pd.DataFrame({
                "日期": [f"Day {i+1}" for i in range(len(ratio_data))],
                "比率": ratio_data
            })
            st.line_chart(df_ratio.set_index("日期"))
            st.caption(f"当前比率: {ratio_data[-1]:.4f}")
        else:
            st.info("暂无比率数据")
    
    with tab_corr:
        st.metric("相关性 (20日)", f"{correlation:.3f}")
        if correlation > 0.8:
            st.success("高相关性，适合套利")
        elif correlation > 0.5:
            st.warning("中等相关性")
        else:
            st.error("低相关性，不建议套利")
    
    # 信号面板
    st.markdown("### 📋 信号面板")
    col_z, col_corr, col_rsi, col_sig = st.columns(4)
    with col_z:
        z_color = "green" if abs(zscore) < 1 else "orange" if abs(zscore) < 3 else "red"
        st.metric("Z-Score", f"{zscore:.2f}")
    with col_corr:
        st.metric("相关性", f"{correlation:.2f}")
    with col_rsi:
        st.metric("RSI", f"{rsi1:.0f} / {rsi2:.0f}")
    with col_sig:
        sig_color = "green" if signal_info["signal"] == "BUY_SPREAD" else "red" if signal_info["signal"] == "SELL_SPREAD" else "gray"
        st.metric("信号", signal_info["signal"], signal_info["reason"])
```

- [ ] **Step 2: 修改 main 函数添加双品种分支**

在 `main()` 函数中，将：

```python
if not timeframe_data:
    st.error("无法获取数据，请稍后重试")
    return
```

之后添加：

```python
# 双品种模式
if enable_spread and symbol2:
    render_pair_analysis(symbol, symbol2, source, source2)
    return  # 双品种模式下不显示单品种内容

if not timeframe_data:
    st.error("无法获取数据，请稍后重试")
    return
```

---

## Task 5: 修改 data.py 添加 fetch_pair_data

**Files:**
- Modify: `kanban/src/data.py`

- [ ] **Step 1: 添加 fetch_pair_data 函数**

在文件末尾添加：

```python
def fetch_pair_data(symbol1: str, symbol2: str, bar: str = "1D", num: int = 100) -> dict:
    """获取双品种数据用于套利分析"""
    source1 = get_source_for_symbol(symbol1)
    source2 = get_source_for_symbol(symbol2)
    
    headers = {"X-Client-ID": CLIENT_ID}
    
    # 获取品种1历史数据
    bars1 = []
    try:
        params1 = {"symbol": symbol1, "source": source1, "bar": bar, "num": num}
        r1 = requests.get(f"{QUANT_CORE_URL}/api/history", params=params1, headers=headers, timeout=30)
        if r1.status_code == 200:
            bars1 = r1.json()
    except Exception:
        pass
    
    # 获取品种2历史数据
    bars2 = []
    try:
        params2 = {"symbol": symbol2, "source": source2, "bar": bar, "num": num}
        r2 = requests.get(f"{QUANT_CORE_URL}/api/history", params=params2, headers=headers, timeout=30)
        if r2.status_code == 200:
            bars2 = r2.json()
    except Exception:
        pass
    
    return {
        "symbol1": symbol1,
        "symbol2": symbol2,
        "bars1": bars1,
        "bars2": bars2,
    }
```

---

## Task 6: 添加测试文件

**Files:**
- Create: `kanban/tests/test_spread_pairs.py`

- [ ] **Step 1: 编写测试**

```python
"""双品种套利分析测试"""
import pytest
import sys
sys.path.insert(0, ".")
from kanban.src.analysis import (
    calculate_spread,
    calculate_ratio,
    calculate_correlation,
    calculate_zscore,
    generate_arbitrage_signal,
)


class TestSpreadCalculations:
    def test_calculate_spread(self):
        bars1 = [{"close": 100}, {"close": 101}, {"close": 102}]
        bars2 = [{"close": 50}, {"close": 51}, {"close": 52}]
        result = calculate_spread(bars1, bars2)
        assert result == [50, 50, 50]
    
    def test_calculate_spread_empty(self):
        assert calculate_spread([], []) == []
    
    def test_calculate_ratio(self):
        bars1 = [{"close": 100}, {"close": 102}, {"close": 104}]
        bars2 = [{"close": 50}, {"close": 51}, {"close": 52}]
        result = calculate_ratio(bars1, bars2)
        assert abs(result[0] - 2.0) < 0.01


class TestZScore:
    def test_calculate_zscore(self):
        spread = [10, 11, 10, 11, 10, 11, 20]  # 最后一个是异常值
        result = calculate_zscore(spread)
        assert "zscore" in result
        assert result["zscore"] > 1  # 异常值应该 zscore > 1
    
    def test_zscore_normal(self):
        spread = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        result = calculate_zscore(spread)
        assert abs(result["zscore"]) < 0.1  # 常数值 zscore 接近 0


class TestArbitrageSignal:
    def test_signal_trigger_zscore_long(self):
        result = generate_arbitrage_signal(zscore=3.5, correlation=0.9, rsi1=60, rsi2=50)
        assert result["signal"] == "SELL_SPREAD"
    
    def test_signal_trigger_zscore_short(self):
        result = generate_arbitrage_signal(zscore=-3.5, correlation=0.9, rsi1=60, rsi2=50)
        assert result["signal"] == "BUY_SPREAD"
    
    def test_signal_watch_low_correlation(self):
        result = generate_arbitrage_signal(zscore=3.5, correlation=0.5, rsi1=60, rsi2=50)
        assert result["signal"] == "WATCH"
    
    def test_signal_watch_low_zscore(self):
        result = generate_arbitrage_signal(zscore=1.0, correlation=0.9, rsi1=60, rsi2=50)
        assert result["signal"] == "WATCH"
```

- [ ] **Step 2: 运行测试验证**

```bash
cd /Users/wang/.opencode/workspace/trading/kanban && python -m pytest tests/test_spread_pairs.py -v
```

---

## Task 7: 集成测试

- [ ] **Step 1: 启动 streamlit 页面测试 UI**

```bash
cd /Users/wang/.opencode/workspace/trading && streamlit run kanban/pages/01_resonance.py --server.port 8501
```

- [ ] **Step 2: 验证功能**
1. 打开 http://localhost:8501/resonance
2. 启用"双品种模式"
3. 选择两个品种
4. 检查价差/比率/相关性 Tab 是否显示
5. 检查信号面板是否正确

---

## 自检清单

- [ ] spec 覆盖：所有设计需求都有对应实现
- [ ] 无占位符：所有代码完整，无 TODO/TBD
- [ ] 类型一致：函数名、参数名全程一致
- [ ] 测试通过：pytest 运行无报错

---

**Plan saved to:** `docs/superpowers/plans/2026-04-24-dual-symbol-arbitrage-plan.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?