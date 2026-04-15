# DOGE/ETH 网格交易机器人

## 概述

DOGE/ETH 比率网格交易机器人 - 监控比率偏离，入场交易，回归均值出场。

## 策略逻辑

- **交易对**: DOGE-USDT / ETH-USDT
- **比率**: DOGE/ETH (DOGE 价格 / ETH 价格)
- **基准价格**: 360 根 K 线前的价格 (使用 15 分钟 K 线)
- **入场信号**: 比率偏离基准 ±1.5%
- **出场信号**: 回归基准 (±0.2%) 或 2小时到期

### 仓位方向

| 偏离方向 | 仓位 | 说明 |
|----------|------|------|
| 比率低 (< -1.5%) | Long DOGE + Short ETH | 做多 DOGE，做空 ETH |
| 比率高 (> +1.5%) | Short DOGE + Long ETH | 做空 DOGE，做多 ETH |

## 文件结构

```
okx_client/
├── __init__.py      # 模块导出
├── okx_trader.py   # OKX API 封装
├── grid_bot.py     # 交易机器人
└── config.yaml     # 配置文件
```

## 配置

编辑 `config.yaml`:

```yaml
okx:
  # 交易模式: 0=实盘, 1=模拟盘
  flag: "1"
  
  # 模拟盘 API 密钥
  sim:
    apikey: "xxx"
    secretkey: "xxx"
    passphrase: "xxx"
  
  # 实盘 API 密钥
  live:
    apikey: "xxx"
    secretkey: "xxx"
    passphrase: "xxx"
  
  # 交易对
  pairs:
    - symbol: "DOGE-USDT"
      min_size: 1
    - symbol: "ETH-USDT"
      min_size: 0.01
```

## 运行

```bash
cd ~/.openclaw/workspace/trading

# 激活虚拟环境
source /Users/openclaw/trading_env/bin/activate

# 设置环境变量
export OKX_API_KEY='xxx'
export OKX_API_SECRET='xxx'
export OKX_PASSPHRASE='xxx'

# 运行机器人
python3 -m okx_client.grid_bot
```

## 后台运行

```bash
# 启动
nohup python3 -m okx_client.grid_bot > ~/.openclaw/logs/grid_bot.log 2>&1 &

# 查看日志
tail -f ~/.openclaw/logs/grid_bot.log

# 停止
pkill -f 'okx_client.grid_bot'
```

## 控制命令

- `/status` - 查看状态
- `/start` - 启动监控
- `/stop` - 停止监控
- `/refresh` - 刷新数据

## 注意事项

1. **模拟盘测试**: 建议先用模拟盘测试
2. **网络**: 实盘 API 需要 VPN/代理 (中国大陆访问限制)
3. **风险**: 使用低杠杆，建议 10x 以下
