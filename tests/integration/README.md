# 集成测试说明

## 测试脚本

`test_webhook_commands.py` - Webhook 命令集成测试

## 使用方法

### 前置条件

1. 启动 webhook 服务：
```bash
cd ~/.openclaw/workspace/trading
source /Users/openclaw/trading_env/bin/activate
python3 notify/webhook_bridge.py &
```

2. 确认服务运行：
```bash
curl http://localhost:5002/health
```

### 运行测试

#### 完整测试（所有阶段）
```bash
python3 tests/integration/test_webhook_commands.py
```

#### 阶段测试
```bash
# 基础命令测试
python3 tests/integration/test_webhook_commands.py --basic

# 监控测试
python3 tests/integration/test_webhook_commands.py --monitor

# IB查询测试
python3 tests/integration/test_webhook_commands.py --ib
```

#### 持续监控模式
```bash
# 每5分钟检查一次，持续1小时
python3 tests/integration/test_webhook_commands.py --watch --interval 300 --duration 3600

# 默认：每5分钟，持续1小时
python3 tests/integration/test_webhook_commands.py --watch
```

#### 指定服务地址
```bash
# 测试远程服务器
python3 tests/integration/test_webhook_commands.py --url http://100.102.240.31:5002
```

#### 保存报告
```bash
python3 tests/integration/test_webhook_commands.py --save my_report.json
```

## 测试阶段

### 阶段 1: 基础命令
- /status
- /help
- /查询模式
- /交易模式

### 阶段 2: 监控命令
- /stop
- /start
- 检查3个交易对是否都显示（MNQ_MYM, HSTECH_MCH, RB_CL）

### 阶段 3: IB 查询
- /持仓
- /账户
- /订单

### 阶段 4: 数据刷新
- /refresh

## 测试报告

报告保存在 `tests/integration/test_results_YYYYMMDD.json`

```bash
# 查看最近报告
ls -la tests/integration/test_results_*.json
cat tests/integration/test_results_*.json | jq
```
