---
name: z120-monitor
description: Z120价差监控系统，支持多交易对价差监控、飞书通知集成。用于：(1) 启动/停止Z120监控 (2) 查询价差状态 (3) 配置交易对 (4) 接收TradingView webhook信号
---

# Z120 价差监控

## 快速启动

### 启动 webhook_bridge 服务
```bash
python3 notify/webhook_bridge.py 5002
```

### 启动 Z120 监控
```bash
# 方式1：通过 webhook 命令
curl http://localhost:5002/webhook -d '{"text": "/start"}'

# 方式2：直接运行
python3 z120_monitor/z120_scheduler.py

# 方式3：只运行一次
python3 z120_monitor/z120_scheduler.py --once
```

## 命令列表

| 命令 | 功能 |
|------|------|
| `/status` | 查看监控状态 |
| `/refresh` | 立即刷新数据 |
| `/start` | 启动监控 |
| `/stop` | 停止监控 |

## 配置

### 交易对配置
文件：`z120_monitor/config/pairs.yaml`

```yaml
pairs:
  - name: "MNQ_MYM"
    mode: "value"
    threshold: 1000
    enabled: true
    assets:
      - symbol: "MNQ"
        exchange: "CME"
        sec_type: "FUT"
        multiplier: 2.0
        ratio1: 1
      - symbol: "MYM"
        exchange: "CME"
        sec_type: "FUT"
        multiplier: 0.5
        ratio2: 2
```

### 价差计算
- **价值价差**：spread = price1 × multiplier1 × ratio1 − price2 × multiplier2 × ratio2
- **价差比率**：spread = (price1 × multiplier1 × ratio1) / (price2 × multiplier2 × ratio2)

## 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/webhook` | POST | 接收 TradingView webhook |
| `/test-api` | POST | 测试 Feishu API |
| `/health` | GET | 健康检查 |

## 测试命令
```bash
# 健康检查
curl http://localhost:5002/health

# 测试发送
curl -X POST http://localhost:5002/test-api -H "Content-Type: application/json" -d '{}'
```

## 相关文件
- 监控脚本：`z120_monitor/z120_scheduler.py`
- 缓存管理：`z120_monitor/z120_cache.py`
- 飞书通知：`notify/feishu.py`
- 状态数据：`data/z120_status.json`
