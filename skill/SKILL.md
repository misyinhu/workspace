---
name: ibkr-trading
description: Trade stocks and futures via Interactive Brokers.
user-invocable: false
command-dispatch: tool
command-tool: exec
command-arg-mode: raw
homepage: https://ib_insync.readthedocs.io
metadata:
  {
    "opencode":
      {
        "emoji": "📈",
        "requires": { "bins": ["python3"] },
      },
  }
---

# IBKR ib_insync 接口调用说明

ib_insync 是 IB Gateway 的独立 Python 实现，兼容最新协议版本。

## 可用功能

- place_order: 下单交易
- get_positions: 获取当前持仓
- get_account_summary: 获取账户摘要
- get_historical_data: 获取历史数据
- get_contract_details: 获取合约详情
- get_orders: 获取订单状态
- get_trades: 获取成交记录
- cancel_order: 取消订单

## 重要调用语法

当用户询问持仓时：
1. exec python3 ~/.opencode/workspace/trading/account/get_positions.py
2. 向用户报告结果。

当用户询问账户摘要时：
1. exec python3 ~/.opencode/workspace/trading/account/get_account_summary.py
2. 向用户报告结果。

当用户想买股票（例如"买入100股AAPL"）：
1. exec python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol AAPL --action BUY --quantity 100 --order_type MKT
2. 向用户报告订单结果。

当用户想卖股票：
1. exec python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol TSLA --action SELL --quantity 50 --order_type MKT
2. 向用户报告结果。

当用户想买期货（例如"买入GC"、"买黄金"）：
1. exec python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol GC --action BUY --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract
2. 向用户报告订单结果。

当用户使用自然语言下单（如"买入1手GC"、"买100股AAPL"、"平仓SIL"、"卖出GC"、"平掉MGC空头"）：
1. 解析用户意图，提取：symbol、action(BUY/SELL)、quantity
2. **推荐使用 --close_position 自动平仓**（自动检测持仓方向，无需手动指定action）：
    - 多头持仓（position > 0）→ 自动执行 SELL 平仓
    - 空头持仓（position < 0）→ 自动执行 BUY 平仓
    - **推荐用法**：exec python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol SIL --close_position --order_type MKT
    - 平部分仓位：exec python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol MGC --close_position --quantity 1 --order_type MKT
    - 不指定quantity时默认全仓平掉
3. 旧版用法（仍支持 --use_position）：
    - 如果是"平仓"操作（action=SELL但持仓为多头，或action=BUY但持仓为空头）：
        a. 使用 --use_position 参数自动查询持仓并使用对应合约
        b. 示例：exec python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol SIL --action BUY --quantity 1 --order_type MKT --use_position
4. 如果是新建仓位：
    a. 期货符号：GC/MGC/QG=期货（COMEX交易所），使用 --sec_type FUT --exchange COMEX --use_main_contract
    b. 股票符号：AAPL/TSLA/SIL=股票（SMART/ARCA交易所），使用 --sec_type STK --exchange SMART
    c. XAUUSD=伦敦金 / XAGUSD=伦敦银（现货金属），使用 --sec_type CMDTY
5. 执行下单命令，确保使用正确的合约信息
6. 向用户报告订单结果。

当用户想查看订单状态：
1. exec python3 ~/.opencode/workspace/trading/orders/get_orders.py
2. 向用户报告订单状态。

当用户想查看历史数据：
1. exec python3 ~/.opencode/workspace/trading/data/get_historical_data.py --symbol AAPL --duration "5 D" --bar_size "1 day"
2. 向用户报告价格数据。

## 参数说明

- symbol: 股票代码 (如 AAPL)
- action: 买卖动作 (BUY/SELL)
- quantity: 数量 (整数)
- order_type: 订单类型 (MKT/LMT/STP/STP LMT)
- tif: 有效时间 (DAY/GTC/IOC/FOK)
- limit_price: 限价价格
- stop_price: 止损价格
- duration: 历史数据时间范围 (1 D = 1天, 1 W = 1周, 1 M = 1月, 1 Y = 1年)
- bar_size: K线时间间隔 (1 min, 5 mins, 1 hour, 1 day)
- exchange: 交易所 (SMART/COMEX/NYMEX等)
- sec_type: 证券类型 (STK/FUT/OPT/CMDTY)
- currency: 货币 (USD/CNY等)
- local_symbol: 当地合约代码 (如 GCM6)
- use_main_contract: 自动选择主力合约 (季月优先)
- use_position: 强制使用持仓合约 (用于平仓操作，已不推荐使用)
- close_position: 自动平仓模式（推荐），自动检测持仓方向

## 期货交易示例

```bash
# 买入1手微型黄金MGC
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol MGC --action BUY --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract

# 自动选择主力合约（推荐）
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol GC --action BUY --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract

# 卖出GC主力合约
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol GC --action SELL --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract

# 平仓（使用持仓合约，确保交易在正确交易所）
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol SIL --action BUY --quantity 1 --order_type MKT --use_position

# 买入伦敦银XAGUSD
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol XAGUSD --action BUY --quantity 100 --order_type MKT --sec_type CMDTY
```

## --close_position 自动平仓模式

```bash
# 自动平掉所有持仓（自动检测方向）
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol MGC --close_position --order_type MKT

# 平部分仓位（平掉1手）
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol AAPL --close_position --quantity 50 --order_type MKT

# 平掉全部AAPL持仓
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol AAPL --close_position --order_type MKT
```

**自动检测逻辑：**
- 多头持仓（position > 0）→ 自动执行 SELL 平仓
- 空头持仓（position < 0）→ 自动执行 BUY 平仓
- 无持仓 → 报错提示

## 使用示例

### 账户余额

```bash
python3 ~/.opencode/workspace/trading/account/get_account_summary.py
```

### 当前持仓

```bash
python3 ~/.opencode/workspace/trading/account/get_positions.py
```

### 历史数据

```bash
python3 ~/.opencode/workspace/trading/data/get_historical_data.py --symbol AAPL --duration "5 D" --bar_size "1 day"
```

### 下单交易

```bash
# 市价买入100股AAPL
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol AAPL --action BUY --quantity 100 --order_type MKT

# 限价买入100股AAPL，价格180
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol AAPL --action BUY --quantity 100 --order_type LMT --limit_price 180

# 卖出50股TSLA
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol TSLA --action SELL --quantity 50 --order_type MKT

# 买入1手微型黄金MGC
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol MGC --action BUY --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract

# 自动选择主力合约（推荐）
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol GC --action BUY --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract

# 卖出GC主力合约
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol GC --action SELL --quantity 1 --order_type MKT --sec_type FUT --exchange COMEX --use_main_contract

# 平仓（使用持仓合约，确保交易在正确交易所）
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol SIL --action BUY --quantity 1 --order_type MKT --use_position

# 买入伦敦银XAGUSD
python3 ~/.opencode/workspace/trading/orders/place_order.py --symbol XAGUSD --action BUY --quantity 100 --order_type MKT --sec_type CMDTY
```

### 订单列表

```bash
python3 ~/.opencode/workspace/trading/orders/get_orders.py
```

### 成交记录

```bash
python3 ~/.opencode/workspace/trading/get_trades.py
```

### 取消订单

```bash
python3 ~/.opencode/workspace/trading/cancel_order.py --order_id 123
```

## 账户信息字段说明

- NetLiquidation: 总账户价值
- AvailableFunds: 可用于交易的现金
- BuyingPower: 购买力
- CashBalance: 现金余额
- EquityWithLoanValue: 含贷款价值的权益

## IB Gateway 配置要求

1. 启动 IB Gateway
2. 勾选 "Enable ActiveX and Socket Clients"
3. 确保端口 4002 (实盘) 或 4001 (模拟) 可用
4. 不勾选 "Read-only API"

## 注意事项

- ib_insync 自动适配 IB Gateway 协议版本，无需手动升级
- 非交易时间市价单可能被自动取消
- 实物交割期货(如MGC)需要账户声明接收意向
- **下单时不需要查询市场数据，直接执行下单命令即可**

## ClientId 管理

IBKR支持多环境连接，自动管理clientId分配：

- **Web opencode**：固定使用 clientId=1（主连接，永不冲突）
- **Mac Terminal**：使用 clientId=2-9（池化管理，最多8个并发连接）
- **冲突处理**：超过8个连接时自动终止最早的连接
- **连接稳定性**：支持Web和本地终端同时操作，互不干扰

## 环境配置

本项目支持本地开发和远程部署两种环境，通过 `config/settings.yaml` 管理：

- **本地开发** (`current: local`): 使用系统 Python，不激活虚拟环境
- **远程部署** (`current: remote`): 使用虚拟环境 Python (`/Users/openclaw/trading_env/bin/python3`)

脚本会自动检测并切换到正确的 Python 环境。如需切换环境，编辑 `config/settings.yaml` 并修改 `current: local` 为 `current: remote`。
