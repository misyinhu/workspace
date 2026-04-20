# Webhook Bridge 核心逻辑文档

> 更新时间：2026-04-20
> 文件位置：`D:/projects/trading/notify/webhook_bridge.py`

## 一、整体架构

```
飞书消息 → webhook_bridge.py → nl_parser.py → place_order_func.py → IB Gateway
                 ↓
              命令路由（查询/交易）
                 ↓
              后台线程下单（避免阻塞）
```

## 二、核心组件

### 2.1 webhook_bridge.py（主服务）

**职责**：接收飞书消息，路由命令，调用下单/查询

**关键函数**：

| 函数 | 作用 |
|------|------|
| `feishu_webhook()` | 处理飞书 POST 请求，解析 JSON 消息 |
| `_submit_order_in_background()` | 后台线程提交订单（不阻塞 HTTP 响应） |
| `_init_ib()` | 启动时预初始化 IB 连接 |

**请求处理流程**：

```python
# 1. 解析飞书消息
event = request.json
message_text = json.loads(event["message"]["content"])["text"]

# 2. 调用解析器
parsed = parse_trading_command(message_text)

# 3. 根据 action 路由
if parsed["action"] in ("BUY", "SELL", "CLOSE"):
    # 下单
    _submit_order_in_background(ib, symbol, action, quantity, 
        exchange=exchange, sec_type=sec_type)
elif parsed["action"] == "QUERY":
    # 查询
    return query_positions() / query_account()
```

**去重机制**：
- 使用 `message_id` 防止重复处理
- 存储最近 100 个 message_id

---

### 2.2 nl_parser.py（命令解析器）

**职责**：从自然语言提取交易参数

**品种分类（2026-04-20 新增）**：

```python
# 外汇品种（使用 CASH 类型，交易所 IDEALPRO）
FOREX_SYMBOLS = {
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 
    'AUDUSD', 'NZDUSD', 'USDCAD', ...
}

# 商品品种（使用 CMDTY 类型，交易所 SMART）
CMDTY_SYMBOLS = {
    'XAUUSD',  # 黄金 vs USD
    'XAGUSD',  # 白银 vs USD
}
```

**解析正则表达式**：

| 模式 | 示例 | 解析结果 |
|------|------|----------|
| `买入(\d+)(?:手\|股)(\S+)` | "买入1手GC" | BUY, qty=1, symbol=GC |
| `卖空(\d+)(?:手\|股)(\S+)` | "卖空2手NQ" | SELL, qty=2, symbol=NQ |
| `平仓(\S+)` | "平仓BTC" | CLOSE, symbol=BTC |
| `查看持仓` | - | QUERY |

**返回结构**：

```python
{
    "action": "BUY" | "SELL" | "CLOSE" | "QUERY" | "UNKNOWN",
    "symbol": "GC",
    "quantity": 1,
    "sec_type": "FUT" | "CASH" | "CMDTY" | "CFD" | "CRYPTO" | None,
    "exchange": "COMEX" | "IDEALPRO" | "SMART" | None,
    "raw": "买入1手GC"
}
```

---

### 2.3 place_order_func.py（下单函数）

**职责**：构造合约，提交订单

**合约类型映射**：

| sec_type | 合约构造 | 示例 |
|----------|----------|------|
| FUT | `Future(symbol, exchange)` | GC, MGC, NQ |
| CASH | `Forex(symbol, exchange)` | USDJPY, EURUSD |
| CMDTY | `Contract(secType='CMDTY')` | XAUUSD, XAGUSD |
| CFD | `CFD(symbol, exchange)` 或 `Contract(conId=...)` | GOLD CFD |
| CRYPTO | `Contract(secType='CRYPTO')` | BTC |

**关键参数**：

```python
place_order(
    ib,              # IB 连接实例
    symbol,          # 品种代码
    action,          # BUY / SELL
    quantity,        # 数量
    exchange=None,   # 交易所
    sec_type=None,   # 合约类型
    conId=None,      # 合约 ID（用于精确匹配）
    close_position=False  # 平仓模式
)
```

**主力合约选择**（期货）：
- 调用 `reqContractDetails()` 获取所有合约
- 选择最近的到期月份
- 通过 `select_main_contract()` 实现

---

## 三、IB 连接架构

### 3.1 ib_connection.py

**设计**：单例模式 + 请求队列

```python
class IBConnectionManager:
    _instance = None
    
    def __init__(self):
        self.ib = IB()
        self.request_queue = Queue()
        self.response_events = {}
        
    def run_sync(self, callable_func, timeout=30):
        """在 IB 线程中执行协程，返回结果"""
        event = threading.Event()
        self.request_queue.put((callable_func, event))
        event.wait(timeout)
        return self.response_events.pop(id(event))
```

**关键**：避免 `util.run()` 的事件循环冲突

**clientId**：使用 `clientId=0`（可看到所有客户端订单）

---

## 四、2026-04-20 修复记录

### 问题 1：XAUUSD 品种映射错误

**现象**：
```
命令: 买入1手XAUUSD
错误: 找不到合约 XAUUSD (CASH)
```

**原因**：
- XAUUSD 不是外汇（Forex），而是商品（Commodity/CMDTY）
- IB 中 `Forex('XAUUSD')` 不存在，需要用 `Contract(secType='CMDTY', symbol='XAUUSD')`

**解决方案**：
```python
# nl_parser.py 新增品种分类
CMDTY_SYMBOLS = {'XAUUSD', 'XAGUSD'}
FOREX_SYMBOLS = {'EURUSD', 'USDJPY', ...}

# 解析时设置正确的 sec_type
if symbol in CMDTY_SYMBOLS:
    result["sec_type"] = "CMDTY"
    result["exchange"] = "SMART"
elif symbol in FOREX_SYMBOLS:
    result["sec_type"] = "CASH"
    result["exchange"] = "IDEALPRO"
```

**验证结果**：
```
买入1手XAUUSD → Commodity(secType='CMDTY', symbol='XAUUSD') → 成交 ✅
买入1手USDJPY → Forex('USDJPY') → 成交 ✅
```

---

### 问题 2：Forex currency 参数错误

**现象**：
```python
# 下单 USDJPY 时，合约变成了
Forex('USDUSD', exchange='IDEALPRO')  # 错误！
```

**原因**：
- `Forex('USDJPY', currency='USD')` 会把货币对覆盖为 USDUSD
- `Forex()` 的 `currency` 参数是**报价货币**，会覆盖原货币对中的报价货币

**错误代码**：
```python
# place_order_func.py 原代码
elif sec_type == "CASH":
    contract = Forex(symbol, exchange=..., currency=currency)  # 错误
```

**修复**：
```python
elif sec_type == "CASH":
    # Forex() 会自动解析货币对，不要传 currency 参数
    contract = Forex(symbol, exchange=exchange or "IDEALPRO")
```

**Forex 用法说明**：
```python
Forex('USDJPY')           # ✅ 正确：symbol='USDJPY'
Forex('USDJPY', currency='USD')  # ❌ 错误：变成 USDUSD
Forex('USD', 'JPY')       # ❌ 报错：AssertionError
```

---

## 五、支持的品种类型

| 类型 | sec_type | 交易所 | 示例 | 数量单位 |
|------|----------|--------|------|----------|
| 期货 | FUT | COMEX/CME | GC, MGC, NQ | 手（整数） |
| 外汇 | CASH | IDEALPRO | USDJPY, EURUSD | 手（整数） |
| 商品 | CMDTY | SMART | XAUUSD, XAGUSD | 手（整数） |
| CFD | CFD | SMART | GOLD CFD | 手（整数） |
| 加密货币 | CRYPTO | PAXOS | BTC | 可小数 |

---

## 六、飞书命令列表

| 命令 | 示例 | 说明 |
|------|------|------|
| 买入 | `买入1手GC` | 开多仓 |
| 卖出 | `卖出1手GC` | 开空仓 |
| 平仓 | `平仓GC` | 平掉指定品种 |
| 查看持仓 | `/持仓` | 查询当前持仓 |
| 查看账户 | `/账户` | 查询账户信息 |
| 查看订单 | `/订单` | 查询未完成订单 |

---

## 七、相关文件路径

| 文件 | 路径 | 作用 |
|------|------|------|
| webhook_bridge.py | `notify/webhook_bridge.py` | 飞书 Webhook 主服务 |
| nl_parser.py | `notify/nl_parser.py` | 自然语言命令解析 |
| place_order_func.py | `orders/place_order_func.py` | 下单逻辑 |
| ib_connection.py | `client/ib_connection.py` | IB 连接管理 |

---

## 八、启动命令

```bash
cd D:/projects/trading/notify
python webhook_bridge.py
```

**服务端口**：5002

**健康检查**：`GET /health`

---

## 九、调试日志

- 日志文件：`notify/webhook_out.log`
- IB 连接日志：控制台输出
- 订单日志：`trade.log` 内联
