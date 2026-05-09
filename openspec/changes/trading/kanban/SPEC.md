# Kanban SPEC

## Scope
Multi-timeframe analysis Dashboard with 6 Streamlit pages.

## Pages
| # | 页面 | 功能 |
|---|------|------|
| 0 | 新闻事件中心 | 市场新闻抓取 |
| 1 | 警报中心 | RSI/价格异常警报 |
| 2 | 市场扫描 | 多品种快速扫描 |
| 3 | 三重滤网 | M30/M5/M1 三周期验证 |
| 4 | 多周期共振 | 共振度 + TV 图表 |
| 5 | 跨周期分析 | 周期对比 + 矛盾检测 |
| 6 | 市场洞察 | 现象 → AI 分析报告 |

## Data Sources
| Source | 品种 | 类型 |
|--------|------|------|
| OKX | DOGE/ETH/BTC | 加密永续 |
| IBKR | MNQ/MYM/RB/HO/MHG/MGC | 芝商所期货 |
| NASDAQ | AAPL/TSLA | 股票 |

## Core Analysis
- **RSI**: period=14
- **MA**: 20/60 均线
- **共振度**: 高≥75%, 中≥50%, 低<50%
- **矛盾检测**: 多周期方向冲突

## Tech Stack
- Streamlit (多页面)
- lightweight-charts (TradingView 图表)
- pandas, numpy
- quant-core API

## Config
- QUANT_CORE_URL: http://100.82.238.11:8005
- CLIENT_ID: 10
- TIMEFRAMES: 1m, 5m, 30m, 4h, 1D