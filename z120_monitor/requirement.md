# Z120 价差监控模块

## 概述

本地代码实现的价差监控系统，监控固定货币对的 Z120 价差，过阈值自动发送飞书通知。

## 监控交易对

| 交易对 | 模式 | 阈值 | 状态 |
|--------|------|------|------|
| MNQ_MYM | value | 1000 | ✅ |
| HSTECH_MCH | value | 10000 | ✅ |
| RB_CL | value | 5000 | ✅ |

## 目录结构

```
z120_monitor/
├── config/
│   └── pairs.yaml          # 交易对配置
├── core/
│   ├── generic_spread.py   # 通用价差计算
│   └── spread_engine.py    # 价差引擎
├── z120_cache.py           # 缓存管理（14天历史）
├── z120_scheduler.py       # 定时调度
└── requirement.md          # 本文档
```

## 配置说明

### pairs.yaml

```yaml
pairs:
  - name: "MNQ_MYM"
    mode: "value"           # value 或 ratio
    threshold: 1000         # 触发阈值
    oversold: -3            # Z120 超卖阈值
    overbought: 3           # Z120 超买阈值
    enabled: true
    assets:
      - symbol: "MNQ"
        exchange: "CME"
        sec_type: "FUT"
        currency: "USD"
        multiplier: 2.0
        ratio: 1
      - symbol: "MYM"
        exchange: "CBOT"
        sec_type: "FUT"
        currency: "USD"
        multiplier: 0.5
        ratio: 2
```

## 价差计算

### 价值价差 (value)
```
spread_value = price1 × multiplier1 × ratio1 − price2 × multiplier2 × ratio2
```

### 价差比率 (ratio)
```
spread_ratio = (price1 × multiplier1 × ratio1) / (price2 × multiplier2 × ratio2)
```

### Z120 计算
```
Z120 = (当前价差 - 7天均值) / 7天标准差
```

- Z120 > 3: OVERBOUGHT（超买）
- Z120 < -3: OVERSOLD（超卖）

## 缓存机制

- **存储路径**: `data/z120_status.json`
- **历史天数**: 14 天
- **更新频率**: 每5分钟

## 使用方法

### 启动监控

```bash
cd ~/.openclaw/workspace/trading
source /Users/openclaw/trading_env/bin/activate
python3 -m z120_monitor.z120_scheduler
```

### 单次执行

```bash
python3 -m z120_monitor.z120_scheduler --once
```

### 飞书命令

- `/start` - 启动 Z120 监控
- `/stop` - 停止 Z120 监控
- `/status` - 查看监控状态
- `/refresh` - 手动刷新数据

## 通知触发条件

满足以下任一条件时发送飞书通知：

1. **Z120 信号**: Z120 < -3 (OVERSOLD) 或 Z120 > 3 (OVERBOUGHT)
2. **价差变化**: 7天价差变化超过阈值

## 与 TradingView 集成的区别

| 特性 | Z120 监控 | TradingView |
|------|-----------|--------------|
| 数据源 | IB Gateway 实时价格 | TradingView webhook |
| 交易对 | 固定配置 (MNQ_MYM 等) | 任意 symbol |
| 触发条件 | Z120 超阈值 | 自定义 alert |
| 实现方式 | 本地代码 | 独立服务 (端口 5003) |

## 已知问题

1. **缓存过期**: 如果超过14天无数据，需要重新运行监控刷新数据
2. **HSTECH_MCH None**: 早期版本因缓存过期导致 zscore 为 None，已修复

## 更新日志

- 2026-02-20: 缓存改为14天，过滤后无数据时使用可用数据
- 2026-02-19: 初始版本，支持3个交易对
