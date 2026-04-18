# 多周期共振分析系统 - Streamlit MVP PRD

## 文档信息
- 版本: v1.0-Streamlit-MVP
- 创建日期: 2025年4月16日
- 技术栈: Python + Streamlit
- 数据源: quant-core (http://100.82.238.11:8000)

---

## 一、执行摘要

### MVP范围

**包含:**
- 品种选择面板（搜索、列表、选择）
- 多周期数据显示（1m/5m/30m/4h 四个固定周期）
- 趋势方向（上涨/下跌/震荡）
- 共振分数计算（0-100）
- OHLCV基础数据显示

**不包含（V2）:**
- 矛盾识别与风险提示
- 交易建议生成
- 下单操作集成
- 自定义周期组合
- 高级图表（K线图、指标线）

---

## 二、技术架构

### 2.1 系统架构

```
Streamlit 前端应用
├── 品种选择面板 (st.sidebar)
│   ├── 搜索框 (st.text_input)
│   ├── 品种列表 (st.selectbox)
│   └── 品种信息 (st.info)
│
└── 多周期分析面板
    ├── 周期卡片 (st.columns(4))
    │   ├── 1分钟: 📈 3250.5 (+0.15%)
    │   ├── 5分钟: 📈 3252.0 (+0.25%)
    │   ├── 30分钟: ➡️ 3252.0 (+0.05%)
    │   └── 4小时: 📈 3252.0 (+1.6%)
    │
    └── 共振分数仪表盘
        └── 共振分数: 75/100 (强共振)

↓ HTTP/REST API

quant-core 远程服务 (http://100.82.238.11:8000)
├── /api/instruments (品种列表)
├── /api/realtime (实时数据)
└── /api/history (历史数据)
```

### 2.2 Streamlit 组件选择

| 功能 | Streamlit 组件 | 说明 |
|------|---------------|------|
| 页面标题 | `st.title()` | 应用标题 "多周期共振分析" |
| 品种搜索 | `st.text_input()` | 侧边栏搜索框 |
| 品种列表 | `st.selectbox()` | 下拉选择品种 |
| 品种信息 | `st.info()` | 显示选中品种信息 |
| 周期卡片 | `st.columns(4)` | 4列布局显示周期 |
| 趋势图标 | `st.markdown()` + emoji | 📈 📉 ➡️ 表示趋势 |
| 共振分数 | `st.metric()` + `st.progress()` | 显示分数和进度条 |
| 加载状态 | `st.spinner()` | 数据加载动画 |
| 错误提示 | `st.error()` / `st.warning()` | 错误和警告信息 |

### 2.3 依赖库

```python
# requirements.txt
streamlit>=1.28.0
requests>=2.31.0
pandas>=2.0.0
numpy>=1.24.0
```

---

## 三、API 接口设计

### 3.1 quant-core 现有接口

根据 `quant/docs/integration-guide.md`，quant-core 提供以下 API：

**基础 URL**: `http://100.82.238.11:8000`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/history` | GET | 获取历史数据 |
| `/api/realtime` | GET | 获取实时数据 |

### 3.2 MVP 需要新增的接口

后端新增聚合接口：

```http
GET /api/instruments
```

响应:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "symbol": "rb2501",
        "name": "螺纹钢2501",
        "exchange": "SHFE",
        "source": "tdxquant"
      }
    ]
  }
}
```

```http
GET /api/multi-timeframe/{symbol}?timeframes=1m,5m,30m,4h
```

响应:
```json
{
  "code": 200,
  "data": {
    "symbol": "rb2501",
    "timeframes": {
      "1m": {"trend": "up", "close": 3252, "ma20": 3245.5},
      "5m": {"trend": "up", "close": 3252, "ma20": 3240.0},
      "30m": {"trend": "neutral", "close": 3252, "ma20": 3245.0},
      "4h": {"trend": "up", "close": 3252, "ma20": 3180.0}
    },
    "resonance": {"score": 75, "level": "high"}
  }
}
```

---

## 四、数据模型

### 4.1 Python 类型定义

```python
from dataclasses import dataclass
from typing import Dict, Literal, Optional
from datetime import datetime

Timeframe = Literal["1m", "5m", "30m", "4h"]
TrendDirection = Literal["up", "down", "neutral"]

@dataclass
class Instrument:
    symbol: str
    name: str
    exchange: str
    source: str

@dataclass
class Resonance:
    score: int  # 0-100
    level: Literal["high", "medium", "low"]
    distribution: Dict[str, int]
```

### 4.2 趋势计算算法

```python
def calculate_trend(close: float, ma20: float) -> str:
    deviation = (close - ma20) / ma20 * 100 if ma20 else 0
    if deviation > 0.5:
        return "up"
    elif deviation < -0.5:
        return "down"
    else:
        return "neutral"
```

---

## 五、UI/UX设计

### 5.1 页面布局

```
┌─────────────────────────────────────────────────┐
│          📊 多周期共振分析系统                    │
├────────────┬────────────────────────────────────┤
│            │                                    │
│  🔍 品种选择  │      多周期分析面板              │
│            │                                    │
│  [搜索框]   │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │
│            │  │ 1m  │ │ 5m  │ │ 30m │ │ 4h  │ │
│  品种列表:  │  │ 📈  │ │ 📉  │ │ ➡️  │ │ 📈  │ │
│  ○ rb2501  │  │3250.│ │3252.│ │3252.│ │3252.│ │
│  ○ AAPL    │  │+0.15│ │+0.25│ │+0.05│ │+1.6%│ │
│  ○ ...     │  └─────┘ └─────┘ └─────┘ └─────┘ │
│            │                                    │
│  ⚙️ 设置    │  ┌─────────────────────────────┐ │
│            │  │   共振分数: 75/100            │ │
│  自动刷新 ✓ │  │   ████████████████████░░░   │ │
│  间隔: 10秒  │  │   等级: 强共振 🟢            │ │
│            │  └─────────────────────────────┘ │
└────────────┴────────────────────────────────────┘
```

### 5.2 组件详细说明

#### 5.2.1 侧边栏 - 品种选择

```python
with st.sidebar:
    st.header("🔍 品种选择")
    
    # 搜索框
    search_keyword = st.text_input(
        "搜索品种",
        placeholder="输入代码或名称...",
        key="search_input"
    )
    
    # 获取并显示品种列表
    instruments = fetch_instruments(search_keyword)
    if instruments:
        selected = st.selectbox(
            "选择品种",
            options=[f"{item['symbol']} - {item['name']}" for item in instruments],
            key="instrument_select"
        )
        
        if selected:
            # 显示品种详细信息
            symbol = selected.split(" - ")[0]
            item = next((i for i in instruments if i['symbol'] == symbol), None)
            if item:
                st.info(f"""
                **{item['name']}**
                - 代码: {item['symbol']}
                - 交易所: {item['exchange']}
                - 数据源: {item['source']}
                """)
    
    # 设置选项
    st.divider()
    st.header("⚙️ 设置")
    
    auto_refresh = st.toggle("自动刷新", value=True, key="auto_refresh")
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔(秒)", 5, 60, 10, key="refresh_interval")
```

#### 5.2.2 主面板 - 周期卡片

```python
def render_timeframe_cards(timeframe_data):
    """渲染周期卡片"""
    if not timeframe_data:
        st.warning("暂无数据，请选择品种")
        return
    
    # 创建4列布局
    cols = st.columns(4)
    
    timeframe_order = ["1m", "5m", "30m", "4h"]
    timeframe_labels = {"1m": "1分钟", "5m": "5分钟", "30m": "30分钟", "4h": "4小时"}
    trend_emojis = {"up": "📈", "down": "📉", "neutral": "➡️"}
    
    for i, tf in enumerate(timeframe_order):
        if tf in timeframe_data:
            data = timeframe_data[tf]
            trend = data['trend']
            close = data['current']['close']
            change_pct = data['change_pct']
            
            with cols[i]:
                st.markdown(f"""
                <div style="
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 1rem;
                    text-align: center;
                    border-left: 5px solid {'#28a745' if trend == 'up' else '#dc3545' if trend == 'down' else '#ffc107'};
                ">
                    <h4 style="margin-bottom: 0.5rem;">{timeframe_labels[tf]}</h4>
                    <div style="font-size: 2.5rem; margin: 0.5rem 0;">
                        {trend_emojis[trend]}
                    </div>
                    <p style="font-size: 1.2rem; font-weight: bold; margin: 0.5rem 0;">
                        {close:.2f}
                    </p>
                    <p style="color: {'#28a745' if change_pct > 0 else '#dc3545' if change_pct < 0 else '#6c757d'}; font-weight: 500;">
                        {change_pct:+.2f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
```

#### 5.2.3 主面板 - 共振分数仪表盘

```python
def render_resonance_gauge(resonance_data):
    """渲染共振分数仪表盘"""
    if not resonance_data:
        return
    
    score = resonance_data['score']
    level = resonance_data['level']
    distribution = resonance_data['distribution']
    
    # 根据等级设置颜色和文字
    if level == 'high':
        color = '#28a745'
        level_text = '强共振'
        bg_gradient = 'linear-gradient(135deg, #28a745, #20c997)'
    elif level == 'medium':
        color = '#ffc107'
        level_text = '中等共振'
        bg_gradient = 'linear-gradient(135deg, #ffc107, #ff9800)'
    else:
        color = '#dc3545'
        level_text = '低共振/分歧'
        bg_gradient = 'linear-gradient(135deg, #dc3545, #f44336)'
    
    st.markdown(f"""
    <div style="
        background: {bg_gradient};
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    ">
        <div style="text-align: center;">
            <h3 style="margin-bottom: 1rem; font-size: 1.5rem;">共振分数</h3>
            <div style="
                font-size: 4rem;
                font-weight: bold;
                margin: 1rem 0;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            ">
                {score}<span style="font-size: 2rem;">/100</span>
            </div>
            <div style="
                font-size: 1.5rem;
                font-weight: 500;
                padding: 0.5rem 1.5rem;
                background: rgba(255,255,255,0.2);
                border-radius: 25px;
                display: inline-block;
                margin: 1rem 0;
            ">
                {level_text}
            </div>
            
            <!-- 进度条 -->
            <div style="margin: 1.5rem 0;">
                <div style="
                    background: rgba(255,255,255,0.3);
                    border-radius: 10px;
                    height: 12px;
                    overflow: hidden;
                ">
                    <div style="
                        background: white;
                        width: {score}%;
                        height: 100%;
                        border-radius: 10px;
                        transition: width 0.5s ease;
                    "></div>
                </div>
            </div>
            
            <!-- 趋势分布 -->
            <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 1rem;">
                <div style="text-align: center;">
                    <span style="font-size: 1.5rem;">📈</span>
                    <div style="font-size: 1.2rem; font-weight: bold;">{distribution.get('up', 0)}</div>
                    <div style="font-size: 0.8rem; opacity: 0.8;">上涨</div>
                </div>
                <div style="text-align: center;">
                    <span style="font-size: 1.5rem;">➡️</span>
                    <div style="font-size: 1.2rem; font-weight: bold;">{distribution.get('neutral', 0)}</div>
                    <div style="font-size: 0.8rem; opacity: 0.8;">震荡</div>
                </div>
                <div style="text-align: center;">
                    <span style="font-size: 1.5rem;">📉</span>
                    <div style="font-size: 1.2rem; font-weight: bold;">{distribution.get('down', 0)}</div>
                    <div style="font-size: 0.8rem; opacity: 0.8;">下跌</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit原生组件显示关键指标
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("共振分数", f"{score}/100", level_text)
    with col2:
        st.metric("主导趋势", f"{distribution.get('up', 0)}涨/{distribution.get('neutral', 0)}震/{distribution.get('down', 0)}跌")
    with col3:
        st.metric("分析周期", "4个 (1m/5m/30m/4h)")
```