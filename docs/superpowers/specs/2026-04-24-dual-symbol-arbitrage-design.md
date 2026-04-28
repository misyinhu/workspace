# 双品种套利分析模式设计

**日期**: 2026-04-24
**状态**: 草稿

---

## 1. 概述

在 `resonance` 页面原有单品种共振分析基础上，增加**双品种套利分析模式**，支持跨品种套利机会识别。

### 1.1 功能范围

- 两个品种的自由选择与组合
- 三种分析视图：价差、比率、相关性
- Z-Score 信号触发（3σ 阈值）
- 多条件组合信号生成

### 1.2 用户场景

用户选中"双品种模式"后，可选择任意两个品种，系统计算价差/比率/相关性，当 Z-Score 超过 3 个标准差且相关性高于 0.8 时，生成套利信号。

---

## 2. UI 布局

```
┌─────────────────────────────────────────────────────────────────┐
│  侧边栏                                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 品种选择                                                    ││
│  │ ┌─────────────────┐  ┌─────────────────┐                   ││
│  │ │  品种 1        │ VS │  品种 2        │                   ││
│  │ │  [下拉选择]    │    │  [下拉选择]    │                   ││
│  │ └─────────────────┘  └─────────────────┘                   ││
│  │                                                             ││
│  │ 数据周期: [1D ▼]  相关性窗口: [20 ▼]                        ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  主内容区                                                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐                        │
│  │ 价差视图 │ │ 比率视图 │ │ 相关性视图   │  (Tab 切换)           │
│  └─────────┘ └─────────┘ └─────────────┘                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │                   图表区域 (ECharts)                       │  │
│  │                                                           │  │
│  │  - 折线图：价差/比率历史                                   │  │
│  │  - 虚线：均值线                                            │  │
│  │  - 区域：±1σ (浅色)、±2σ (深色)                           │  │
│  │  - 悬停：日期、各价格、差值、Z-Score                       │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 信号面板                                                    │  │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │  │
│  │ │ Z-Score    │ │ 相关性     │ │ RSI(S1/S2) │ │ 综合信号 │ │  │
│  │ │ 1.85  ⚠️   │ │ 0.92  ↗️   │ │ 65 / 58    │ │ WATCH    │ │  │
│  │ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 组件清单

### 3.1 品种选择器 (DualSymbolSelector)

| 属性 | 说明 |
|------|------|
| 类型 | 两个独立的 `st.selectbox` |
| 数据源 | 共用单品种模式的 instruments 配置 |
| 默认值 | 品种1: DOGE-USDT-SWAP, 品种2: ETH-USDT-SWAP |

### 3.2 分析视图 Tabs (AnalysisTabs)

| Tab | 内容 |
|-----|------|
| 价差 | Spread = S1 - S2 折线图 + 均值线 + Z-Score 标注 |
| 比率 | Ratio = S1 / S2 折线图 + 均值线 |
| 相关性 | 滚动相关性热力图 + 散点图 |

### 3.3 信号面板 (SignalPanel)

| 指标 | 格式 | 颜色规则 |
|------|------|----------|
| Z-Score | X.XX | 绿 < 1, 黄 1-3, 红 > 3 |
| 相关性 | X.XX | 绿 > 0.8, 黄 0.5-0.8, 红 < 0.5 |
| RSI | S1 / S2 | 各自独立显示 |
| 综合信号 | BUY_SPREAD / SELL_SPREAD / WATCH | 对应颜色 |

---

## 4. 数据流

### 4.1 数据获取

```python
def fetch_pair_data(symbol1: str, symbol2: str) -> dict:
    """获取双品种数据"""
    data1 = fetch_multi_timeframe(symbol1)
    data2 = fetch_multi_timeframe(symbol2)
    
    return {
        "symbol1": symbol1,
        "symbol2": symbol2,
        "data1": data1,
        "data2": data2,
        "timeframes": {
            "1D": {"spread": ..., "ratio": ..., "correlation": ...},
            "4H": {...},
            ...
        }
    }
```

### 4.2 计算模块

```python
def calculate_spread(bars1: list, bars2: list) -> list:
    """计算价差序列"""
    closes1 = [b["close"] for b in bars1]
    closes2 = [b["close"] for b in bars2]
    return [c1 - c2 for c1, c2 in zip(closes1, closes2)]

def calculate_ratio(bars1: list, bars2: list) -> list:
    """计算比率序列"""
    closes1 = [b["close"] for b in bars1]
    closes2 = [b["close"] for b in bars2]
    return [c1 / c2 if c2 != 0 else 0 for c1, c2 in zip(closes1, closes2)]

def calculate_correlation(bars1: list, bars2: list) -> float:
    """计算皮尔逊相关系数"""
    closes1 = [b["close"] for b in bars1]
    closes2 = [b["close"] for b in bars2]
    # N日滚动相关性
    ...

def calculate_zscore(spread_series: list) -> dict:
    """计算 Z-Score"""
    mean = np.mean(spread_series)
    std = np.std(spread_series)
    current = spread_series[-1]
    zscore = (current - mean) / std if std != 0 else 0
    return {"zscore": zscore, "mean": mean, "std": std}
```

### 4.3 信号生成

```python
def generate_arbitrage_signal(zscore, correlation, rsi1, rsi2) -> str:
    """多条件组合信号"""
    signals = []
    
    # 条件1: Z-Score > 3σ
    if abs(zscore) > 3.0:
        signals.append(("ZSCORE_LONG" if zscore > 0 else "ZSCORE_SHORT", zscore))
    
    # 条件2: 相关性 > 0.8
    if correlation > 0.8:
        signals.append(("CORRELATION_OK", correlation))
    
    # 条件3: RSI 背离 > 20
    if abs(rsi1 - rsi2) > 20:
        signals.append(("RSI_DIVERGE", abs(rsi1 - rsi2)))
    
    # 综合判断
    has_zscore = any("ZSCORE" in s[0] for s in signals)
    has_corr = any("CORRELATION" in s[0] for s in signals)
    
    if has_zscore and has_corr:
        if any("ZSCORE_LONG" in s[0] for s in signals):
            return "SELL_SPREAD"  # 价差高 + 高相关 → 卖价差
        else:
            return "BUY_SPREAD"   # 价差低 + 高相关 → 买价差
    
    return "WATCH"
```

---

## 5. 信号阈值

| Z-Score | 状态 | 颜色 |
|---------|------|------|
| \|Z\| < 1 | 正常 | 绿色 |
| 1 ≤ \|Z\| < 3 | 偏离 | 黄色 |
| \|Z\| ≥ 3 | 信号触发 | 红色 |

| 综合信号 | 触发条件 | 操作 |
|----------|---------|------|
| BUY_SPREAD | Z < -3 且 相关性 > 0.8 | 买 S1 卖 S2 |
| SELL_SPREAD | Z > +3 且 相关性 > 0.8 | 卖 S1 买 S2 |
| WATCH | 其他 | 观望 |

---

## 6. 图表配置

### 6.1 价差折线图

```python
chart_options = {
    "xAxis": {"type": "time", "data": dates},
    "yAxis": {"type": "value", "name": "价差"},
    "series": [
        {"name": "Spread", "type": "line", "data": spread_data},
        {"name": "Mean", "type": "line", "lineStyle": {"type": "dashed"}, "data": mean_line},
    ],
    "markArea": {
        "data": [
            [{"yAxis": mean - std, "itemStyle": {"color": "rgba(0,255,0,0.1)"}}, 
             {"yAxis": mean + std}],
            [{"yAxis": mean - 2*std, "itemStyle": {"color": "rgba(255,255,0,0.1)"}}, 
             {"yAxis": mean - std}],
            [{"yAxis": mean + std, "itemStyle": {"color": "rgba(255,255,0,0.1)"}}, 
             {"yAxis": mean + 2*std}],
        ]
    }
}
```

### 6.2 相关性散点图

```python
scatter_options = {
    "xAxis": {"type": "value", "name": "S1 价格"},
    "yAxis": {"type": "value", "name": "S2 价格"},
    "series": [{
        "type": "scatter",
        "data": [[s1, s2] for s1, s2 in zip(closes1, closes2)],
        "symbolSize": 5,
    }]
}
```

---

## 7. 文件变更

| 文件 | 变更 |
|------|------|
| `kanban/pages/01_resonance.py` | 修改 `render_sidebar()` 增加第二个品种选择器；增加双品种 Tab 视图 |
| `kanban/src/data.py` | 增加 `fetch_pair_data()`, `fetch_pair_history()` |
| `kanban/src/analysis.py` | 增加 `calculate_spread()`, `calculate_ratio()`, `calculate_correlation()`, `calculate_zscore()`, `generate_arbitrage_signal()` |
| `kanban/src/config.py` | 增加 `ARBITRAGE_DEFAULTS` (zscore_threshold=3.0, correlation_threshold=0.8) |
| `kanban/tests/test_spread_pairs.py` | 新增测试文件 |

---

## 8. 依赖

- `streamlit` - UI 框架
- `pandas` - 数据处理
- `numpy` - 计算（相关性、均值、标准差）
- `plotly` 或 `echarts` - 图表（复用现有配置）

---

## 9. 测试场景

| 场景 | 预期结果 |
|------|---------|
| 选择 DOGE-USDT + ETH-USDT | 显示两个品种数据、价差、相关性 |
| Z-Score = 3.5，相关性 = 0.9 | 显示 BUY_SPREAD 信号 |
| Z-Score = -3.2，相关性 = 0.85 | 显示 SELL_SPREAD 信号 |
| 相关性 = 0.5 | 显示 WATCH 信号 |
| 数据加载失败 | 显示错误提示，不崩溃 |

---

**Review Status**: 待用户确认后进入实现阶段