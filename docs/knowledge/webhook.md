# IB 连接架构设计与下单系统调试实录

> 从一个下单 Bug 到架构设计的深度思考

## 背景

我们的 Quant 产品线正在建设中，目标是为不同层级的用户提供量化交易服务：

| 产品 | 目标用户 | 核心功能 |
|------|----------|----------|
| quant-agent | 新手小白 | AI 对话式交易 |
| quant-research | 进阶用户 | 套利研究工具 |
| quant-edge-pro | 机构用户 | 基金运营平台 |
| quant-core | 内部服务 | 核心基础设施 |

所有产品都需要通过 IB (Interactive Brokers) 进行交易执行，这引发了一个核心架构问题：**多个应用如何共享 IB 连接？**

---

## 问题起源：一个下单系统的调试之旅

### 初期问题

我们的飞书 Webhook 下单系统在收到 "买入 GC" 指令时，会出现 30 秒超时。整个调试过程持续了多天，涉及多个技术层面的探索。

### 第一阶段：语法错误与缩进修复

最初的错误是 Python 语法问题——`place_order_func.py` 中存在重复的 `else:` 块和缩进错误。这类问题在多次修改后很常见，每次增量修复都引入新的问题。

**教训**：当文件已经混乱时，不要继续打补丁。重写整个函数比逐行修复更可靠。

### 第二阶段：asyncio 事件循环冲突

修复语法错误后，真正的问题浮出水面：`place_order()` 函数在调用 `ib.reqContractDetails()` 时会永久挂起。

**根因分析**：

```python
# ib_insync 内部的 util.run()
def run(coroutine):
    loop = getLoop()  # 获取当前线程的事件循环
    return loop.run_until_complete(coroutine)
```

问题在于：
1. IB 连接在后台线程运行 `ib.run()`（内部是 `loop.run_forever()`）
2. Flask worker 线程调用 `ib.reqContractDetails()` → `util.run()`
3. `util.run()` 在 Flask worker 线程创建新的事件循环
4. 但 IB 的 socket reader 还在后台线程的循环上等待
5. 永久阻塞

### 第三阶段：尝试 nest_asyncio

我们尝试使用 `nest_asyncio` 允许嵌套事件循环：

```python
import nest_asyncio
nest_asyncio.apply()
```

结果：仍然失败。`run_in_executor` 线程没有设置事件循环，导致 `getLoop()` 返回错误的对象。

### 第四阶段：请求队列架构

最终解决方案是放弃 `run_forever()`，改用请求队列模式：

```python
class IBConnectionManager:
    def __init__(self):
        self._request_queue = queue.Queue()
        self._client_id = 999
    
    def _run_loop(self):
        """IB 工作线程 - 处理请求队列"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ib = IB()
        self._ib.connect(self._host, self._port, clientId=self._client_id)
        
        while self._running:
            try:
                request = self._request_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            fn, result_queue = request['fn'], request['result_queue']
            with self._loop_lock:  # 防止与事件泵冲突
                result = fn()  # 直接调用，util.run() 会用当前线程的 loop
            result_queue.put(('ok', result))
    
    def run_sync(self, fn, timeout=30.0):
        """在其他线程中提交请求"""
        result_queue = queue.Queue()
        self._request_queue.put({'fn': fn, 'result_queue': result_queue})
        status, value = result_queue.get(timeout=timeout)
        return value
```

**关键洞察**：
- 不使用 `run_forever()`
- 每个请求独立调用 `util.run()` → `run_until_complete()`
- `run_until_complete()` 执行期间会处理 socket 事件
- 请求完成后线程继续等待下一个请求
- clientId 统一为 999，所有功能共享同一连接

### 第五阶段：事件泵与成交回调

队列方案解决了下单阻塞问题，但引入了新问题：**IB 线程空闲时不处理 socket 事件，导致 execDetails 回调无法触发。**

#### 问题分析

IB 的 socket 读取通过 `loop.add_reader()` 注册在 asyncio 事件循环上。`run_until_complete()` 只在请求执行期间处理事件，空闲时事件循环不运转，回调永远无法触发。

这意味着下单后：
- ✅ `placeOrder()` 通过 `run_sync()` 提交 → 成功
- ❌ 成交回报 `execDetails` 无法触发 → 飞书收不到实时通知

#### 事件泵方案

添加独立的泵线程，在空闲时定期驱动事件循环：

```python
def _event_pump(self):
    """定期驱动事件循环，处理待分发的 IB 事件"""
    logger.info("[IB-Pump] Event pump started")
    while self._running:
        time.sleep(0.2)
        try:
            if self._loop_lock.acquire(timeout=0.05):
                try:
                    self._loop.run_until_complete(asyncio.sleep(0))
                except RuntimeError:
                    pass
                finally:
                    self._loop_lock.release()
        except Exception:
            pass
```

#### Python 3.12 兼容性陷阱

⚠️ **关键修复**：`asyncio.sleep()` 在 Python 3.10+ 移除了 `loop` 关键字参数：

```python
# ❌ Python 3.12 报 TypeError，但被 except 吞掉 → pump 静默失败
self._loop.run_until_complete(asyncio.sleep(0, loop=self._loop))

# ✅ 正确写法
self._loop.run_until_complete(asyncio.sleep(0))
```

这个问题非常隐蔽——`TypeError` 被外层 `except Exception` 捕获后 pump 线程继续运行，但从未真正泵过事件。日志显示 "Event pump started" 但没有后续输出，看似正常实则无效。

#### execDetails 回调注册

```python
def _register_fill_callback(self):
    """注册成交回报回调，通过飞书实时推送"""
    def on_fill(trade, fill):
        execution = fill.execution
        side = "买入 (BOT)" if execution.side == "BOT" else "卖出 (SLD)"
        text = (
            f"📈 **成交回报**\n"
            f"标的: {fill.contract.localSymbol}\n"
            f"方向: {side}\n"
            f"数量: {execution.shares}\n"
            f"价格: {execution.price}"
        )
        send_feishu(text, DEFAULT_CHAT_ID)
    
    self._ib.execDetailsEvent += on_fill
    logger.info("[IB] Registered execDetails callback for fill notifications")
```

#### 重复通知问题

修复事件泵后，execDetails 回调正常触发，但出现了重复通知：

1. **📈 成交回报** — execDetails 回调推送（实时）
2. **🤖 下单结果** — 5秒轮询后推送（延迟重复）

**解决方案**：删除轮询逻辑，只保留回调推送：

- 删除 `place_order_func.py` 中的 5 秒轮询等待代码
- 删除 `webhook_bridge.py` 中的"下单结果"通知
- 保留"⏳ 订单提交中"作为提交确认
- 成交结果完全由 execDetails 回调推送

最终通知流程：下单 → ⏳ 订单提交中 → IB 成交 → 📈 成交回报

---

## 品种分类问题

在解决连接问题后，又遇到品种识别问题：XAUUSD 被错误识别为外汇（CASH），导致找不到合约。

### 问题分析

```python
# 错误的代码
Forex('XAUUSD', currency='USD')  # 变成 Forex('USDUSD')！
```

IB 的 `Forex()` 构造函数中，`currency` 参数会覆盖货币对中的报价货币。

### 解决方案

```python
# 正确的品种分类
FOREX_SYMBOLS = {'USDJPY', 'EURUSD', 'GBPUSD', ...}  # 外汇
CMDTY_SYMBOLS = {'XAUUSD', 'XAGUSD'}                  # 商品
CFD_SYMBOLS = {'GOLD', 'SILVER'}                      # CFD

def get_contract(symbol):
    if symbol in CMDTY_SYMBOLS:
        return Commodity(symbol)  # XAUUSD → Commodity
    elif symbol in FOREX_SYMBOLS:
        return Forex(symbol)      # 不要传 currency 参数！
    elif symbol in CFD_SYMBOLS:
        return CFD(symbol)
    else:
        return Future(symbol)     # 默认期货
```

**教训**：IB API 的参数语义需要仔细阅读文档，想当然的假设往往是错的。

---

## clientId 管理：架构层面的思考

解决下单问题后，我们开始思考更大的架构问题：**多个应用如何共享 IB 连接？**

### IB clientId 的本质

| clientId | 用途 | 特点 |
|----------|------|------|
| 0 | TWS 自己 / 管理员 | 能看到所有订单 |
| 1-31 | API 客户端 | 每个连接独立管理订单 |
| 32+ | 部分版本支持 | 可能有兼容性问题 |

**关键规则**：
1. 同一个 clientId 只能有一个活跃连接
2. 不同 clientId 可以同时连接同一个 Gateway
3. clientId=0 可以看到所有客户端的订单

### 产品矩阵的 clientId 分配

```
┌─────────────────────────────────────────────────┐
│                  IB Gateway                      │
│              (127.0.0.1:4002)                   │
└─────────────────────────────────────────────────┘
          │
          ├── clientId=0  →  监控/管理服务
          │
          ├── clientId=1  →  quant-agent
          │
          ├── clientId=2  →  quant-research
          │
          ├── clientId=3  →  quant-edge-pro
          │
          └── clientId=4  →  webhook 服务
```

### 架构方案

#### 方案 A：Core 服务维护连接池

```python
class IBConnectionPool:
    CLIENTS = {
        'monitor': 0,   # 能看到所有订单
        'agent': 1,
        'research': 2,
        'edge-pro': 3,
        'webhook': 4,
    }
    
    def __init__(self, host, port):
        self._connections = {}
    
    async def get_connection(self, app_id: str) -> IB:
        client_id = self.CLIENTS.get(app_id, 4)
        if client_id not in self._connections:
            ib = IB()
            await ib.connectAsync(host, port, clientId=client_id)
            self._connections[client_id] = ib
        return self._connections[client_id]
```

**优点**：
- 集中管理，便于监控
- 应用隔离，一个崩溃不影响其他
- 订单来源清晰

**缺点**：
- Core 服务是单点
- 需要维护多个连接

#### 方案 B：单一连接 + orderRef 标识

```python
class IBSingleManager:
    def __init__(self, client_id=0):
        self._ib = IB()
        self._ib.connect(host, port, clientId=client_id)
    
    def place_order(self, app_id: str, contract, order):
        order.orderRef = f"app:{app_id}"  # 标记来源
        return self._ib.placeOrder(contract, order)
    
    def get_orders_by_app(self, app_id: str):
        return [t for t in self._ib.reqAllOpenOrders()
                if t.order.orderRef == f"app:{app_id}"]
```

**优点**：
- 简单，只需一个连接
- 资源占用少

**缺点**：
- 应用之间没有隔离
- 无法追踪不同应用的订单状态

### 识别请求来源

Core 服务需要知道请求来自哪个应用：

**方法 1：HTTP Header**
```python
@app.post("/order")
async def place_order(request: Request, body: OrderRequest):
    app_id = request.headers.get("X-App-ID", "unknown")
    return await ib_pool.execute(app_id, body)
```

**方法 2：消息队列**
```python
# 上层应用发送
redis.publish("ib:order", json.dumps({
    "app_id": "quant-agent",
    "symbol": "GC",
    "qty": 1
}))

# Core 订阅处理
for msg in redis.subscribe("ib:order"):
    data = json.loads(msg)
    await ib_pool.execute(data["app_id"], place_order, data)
```

---

## 最佳实践总结

### 1. 事件循环管理

```python
# ❌ 错误：在不同线程调用 util.run()
def worker():
    result = ib.reqContractDetails(contract)  # 可能阻塞

# ✅ 正确：使用请求队列
def worker():
    result = manager.run_sync(lambda: ib.reqContractDetails(contract))
```

### 1.5 Python 版本兼容性

| Python 版本 | `asyncio.sleep()` | `util.run()` / `getLoop()` |
|-------------|-------------------|---------------------------|
| 3.9 - 3.9.x | ✅ `loop=` 参数可用 | ✅ 正常 |
| 3.10+ | ⚠️ `loop=` 参数已弃用 | ⚠️ 可能报 DeprecationWarning |
| 3.12+ | ❌ `loop=` 参数已移除（TypeError） | ❌ 非主线程 RuntimeError |

**关键教训**：
- `asyncio.sleep(0, loop=loop)` → 改为 `asyncio.sleep(0)`，loop 通过 `asyncio.set_event_loop()` 设置
- ib_insync 的 `util.getLoop()` 在 Python 3.13+ 非主线程会报 RuntimeError，需 patch 加 `new_event_loop()` 兜底
- 异常被 `except Exception` 吞掉后，功能静默失败极难排查——日志显示"已启动"但实际无效

### 2. clientId 分配

| 场景 | 推荐 clientId |
|------|--------------|
| 生产交易 | 1-10（固定分配） |
| 测试/模拟 | 11-20 |
| 监控/管理 | 0 |
| 临时脚本 | 临时分配 |

### 3. 品种识别

```python
# 品种分类表
ASSET_TYPES = {
    # 外汇 - 不传 currency 参数
    'forex': ['USDJPY', 'EURUSD', 'GBPUSD'],
    
    # 商品
    'cmdty': ['XAUUSD', 'XAGUSD'],
    
    # CFD
    'cfd': ['GOLD', 'SILVER'],
    
    # 期货（默认）
    'future': ['GC', 'MGC', 'SI'],
}
```

### 4. 错误处理

```python
# 订单重试机制
MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    try:
        trade = ib.placeOrder(contract, order)
        return trade
    except Exception as e:
        if attempt == MAX_RETRIES - 1:
            raise
        time.sleep(1)  # 等待后重试
```

---

## 后续工作

1. **quant-core 模块化**：将 IB 连接管理抽象为独立模块
2. **监控仪表盘**：实时查看各 clientId 的连接状态和订单
3. **权限控制**：不同应用有不同的交易权限
4. **审计日志**：记录所有订单的操作来源和时间

---

## 调试时间线总览

| 时间 | 阶段 | 关键修复 |
|------|------|----------|
| 4/16 02:47-06:03 | 初始错误排查 | 语法错误、asyncio 事件循环添加 |
| 4/16 06:03-06:54 | Qt 事件循环冲突 | `ib.sleep()` → `time.sleep()` |
| 4/16 06:54-08:16 | clientId 冲突 | clientId=55 被占用 → Error 326 |
| 4/16 08:16-09:58 | asyncio 深层冲突 | patch `util.getLoop()` 加兜底 |
| 4/17 15:08-16:55 | webhook 缩进修复 | 多处缩进错误、缺失 return |
| 4/17-4/18 | place_order 挂起 | 根因定位：`util.run()` 线程本地特性 |
| 4/20 07:01-10:17 | **队列架构重构** | `run_sync()` + `queue.Queue` 方案 |
| 4/20 10:54-11:22 | XAUUSD 品种修复 | CMDTY ≠ CASH，Forex currency 覆盖问题 |
| 4/20 13:20-13:54 | **GC 平仓修复** | conId 合约构建 + exchange 强制设置 + CLOSE 判断 |
| 4/20 15:08-16:40 | 查询命令内联 | 持仓/账户/订单/成交 → run_sync() |
| 4/20 16:50-17:14 | 成交回调 | execDetails 注册 + 事件泵 |
| 4/21 01:17 | **重复通知修复** | 删除 5 秒轮询，只保留回调推送 |
| 4/21 01:19 | Python 3.12 兼容性 | `asyncio.sleep(0, loop=...)` → `asyncio.sleep(0)` |
| 4/20 22:45-23:07 | GC 平仓失败排查 | "1单元GC" 无法匹配持仓 symbol="GC" |
| 4/20 23:07-23:33 | **nl_parser 格式扩展** | 支持 "X单元Y" / "品种+数量" 三种格式 |
| 4/20 23:07-23:33 | 持仓查询修复 | `ib.positions()` 未走 `_run_ib()` 导致事件循环冲突 |
| 4/21 07:33 | 代码同步+重启 | git bundle + stash pull，webhook 重启 PID 24388 |

---

## 第七阶段：nl_parser 格式扩展与持仓查询修复

### 问题：自然语言解析不覆盖数量后置格式

用户发送 "平仓1单元gc" 时，`nl_parser.py` 将整体匹配为 `symbol="1单元GC"`，导致持仓匹配时 `pos.contract.symbol == "1单元GC"` 找不到任何持仓。

### 根因

原始正则只匹配 `动作+数量+品种` 格式（如 "平仓1手GC"），不支持：
- `动作+品种+数量`（如 "平仓GC1手"、"买入GC1单元"）
- 纯品种（如 "平仓GC"）

### 修复：三种格式全覆盖

```python
TRADING_PATTERNS = [
    # 格式1: 数量+品种（平仓1手GC、卖出2单元MGC）
    r'(平仓|卖出|做空|做多|买入)\s*(\d+)\s*(单元|手|张)?\s*(\w+)',
    # 格式2: 品种+数量（平仓GC1手、买入GC2单元）
    r'(平仓|卖出|做空|做多|买入)\s*(\w+?)\s*(\d+)\s*(单元|手|张)',
    # 格式3: 纯品种（平仓GC、买入MGC）
    r'(平仓|卖出|做空|做多|买入)\s*(\w+)',
]
```

同时在 symbol 清理逻辑中去除"单元"、"手"、"张"等数量单位后缀，确保纯 symbol 提取。

### 持仓查询事件循环冲突

**症状**：飞书发送 "持仓" 返回 "❌ 获取持仓失败:"

**根因**：审计所有 IB API 调用发现 `get_positions_formatted()` 第 435 行直接在 Flask 线程调用 `ib.positions()`，而其他查询函数（accountSummary、trades、fills）都正确使用了 `_run_ib()`。

```python
# ❌ 直接调用 → 事件循环冲突
positions = ib.positions()

# ✅ 通过队列提交到 IB 工作线程
positions = _run_ib(lambda: ib.positions(), timeout=15)
```

**教训**：每次添加新的 IB API 调用时，都必须确认是否通过 `run_sync()` / `_run_ib()` 提交。Flask 线程永远不能直接调用 ib_insync API。

---

## 部署脚本问题

### deploy-to-cxclaw.sh 的两个 Bug

```bash
# Bug 1: REMOTE_DIR 被覆盖
REMOTE_DIR="${CXCLAW_DIR:-\$HOME}"    # ← 这行被下面覆盖
# ... 中间代码 ...
REMOTE_DIR="~/deploy_temp"             # ← 覆盖了上面的环境变量配置

# Bug 2: Windows 路径硬编码为 /d/ 但实际是 D:/
tar -xzf $REMOTE_DIR/trading_deploy_cxclaw.tar.gz  # 解压到 /d/projects/trading
# 应该用 D:/projects/trading
```

---

## 当前系统状态

**连接**：IB Gateway 127.0.0.1:4002, clientId=999  
**Webhook**：Flask port 5002（Windows 远程部署）  
**架构**：队列模式 + 事件泵 + execDetails 回调  

**通知流程**：
```
飞书/TV → webhook → run_sync() → IB 线程 → placeOrder()
                                          ↓
                                    IB 成交 → execDetails 回调 → 飞书推送 📈
```

**品种映射**：

| 品种 | sec_type | exchange | 特殊处理 |
|------|----------|----------|----------|
| XAUUSD/XAGUSD | CMDTY | — | 非 Forex，不传 currency |
| USDJPY/EURUSD等 | CASH | — | Forex 标准处理 |
| GOLD/SILVER | CFD | SMART | CFD 合约 |
| GC/MGC | FUT | COMEX | 需 conId + exchange |
| BTC | FUT | CMECRYPTO | 期货标准处理 |

**关键文件**：
- `client/ib_connection.py` — 队列架构 + 事件泵 + clientId=999
- `orders/place_order_func.py` — conId 合约构建 + exchange 强制设置（无轮询）
- `notify/webhook_bridge.py` — CLOSE 判断 + outside_rth + 成交回调（无重复通知）
- `notify/nl_parser.py` — 自然语言解析 + 品种映射

---

## 参考资料

- [IB API 官方文档](https://interactivebrokers.github.io/tws-api/)
- [ib_insync 库](https://ib_insync.readthedocs.io/)
- [asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)

---

*本文记录了从调试一个具体的下单 Bug，到思考整个 Quant 产品线 IB 连接架构的过程。希望能对同样在做量化系统开发的同行有所帮助。*
