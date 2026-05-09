# IB 连接下单问题分析总结

## 问题描述

飞书发送"买入gc"命令 → webhook 接收到 → 永久卡住 → HTTP 超时返回 500。

## 根因分析

### ib_insync 事件循环架构

1. `ib.connect()` 内部调用 `util.run()` → `loop.run_until_complete(connectAsync())`
2. `connectAsync()` 完成后，连接建立，但**没有持续运行的事件循环**
3. 后续调用 `ib.reqContractDetails()` → `util.run()` → 在**当前线程的临时事件循环**中等待
4. 回调由 IB Gateway 发送到 TCP 连接，ib_insync 在接收线程处理 → 但当前线程的临时循环收不到
5. **结果**：永久阻塞

### 专家子代理结论

> 把 `ib.connect()` + `ib.run()` 放到独立 daemon 线程中，ib_insync 会自动处理跨线程调用。

### 关键点

**`ib.run()` 不带参数调用时，会运行 `loop.run_forever()`** —— 这是让事件循环永久运行的唯一方法。

## 修复方案

### 方案一：独立线程运行 `ib.run()`（ib_connection.py）

```python
def _run_ib(self):
    self._loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self._loop)
    self._ib = IB()
    self._ib._loop = self._loop  # 关键：存储 loop 引用
    self._ib.connect(host, port, clientId=99, timeout=10)
    self._ready.set()
    self._loop.run_forever()  # 永久运行事件循环
```

### 方案二：所有 `ib.xxx()` 调用改为 `ib.xxxAsync()` + `asyncio.run_coroutine_threadsafe()`

```python
def _run_ib_async(ib, coro_or_func, timeout=30.0):
    loop = getattr(ib, '_loop', None)  # 优先用 ib._loop
    if loop is None or not loop.is_running():
        from ib_insync import util as ib_util
        loop = ib_util.getLoop()
    
    # 支持传入函数（返回协程）或直接传入协程
    coro = coro_or_func() if callable(coro_or_func) else coro_or_func
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)

# 使用示例
details = _run_ib_async(ib, ib.reqContractDetailsAsync(contract), timeout=10)
trade = _run_ib_async(ib, ib.placeOrderAsync(contract, order), timeout=30)
```

### place_order_func.py 中的改动

| 原代码 | 新代码 |
|--------|--------|
| `ib.reqContractDetails(base_contract)` | `_run_ib_async(ib, ib.reqContractDetailsAsync(base_contract), timeout=10)` |
| `ib.placeOrder(contract, order)` | `_run_ib_async(ib, ib.placeOrderAsync(contract, order), timeout=30)` |
| `ib.positions()` | `_run_ib_async(ib, ib.positionsAsync(), timeout=10)` |

## 当前状态（2026-04-20）

- ib_connection.py 已更新为独立线程 + run_forever() + ib._loop 存储
- place_order_func.py 已改为全部使用 `_run_ib_async()`
- 但测试发现错误：`TypeError: A coroutine object is required`
- 说明 `_run_ib_async` 的 fallback 逻辑还有问题，需要继续排查

## 调试方法

```bash
# 本地快速测试 IB 连接
ssh Apple@100.82.238.11 'cd D:/projects/trading && python test_ib1.py'

# 测试完整下单流程（前台运行看日志）
ssh Apple@100.82.238.11 'cd D:/projects/trading/notify && python webhook_bridge.py'

# 测试 HTTP 请求
ssh Apple@100.82.238.11 'python -c "import requests,json; r=requests.post(\"http://127.0.0.1:5002/feishu-webhook\", json={\"header\":{\"event_type\":\"im.message.receive_v1\"},\"event\":{\"message\":{\"message_id\":\"test\",\"chat_id\":\"oc_test\",\"content\":\"{\\\"text\\\":\\\"\\\u4e70\\\u5165gc\\\"}\"}}}, timeout=30); print(r.text[:300])"'
```

## 其他发现

- clientId 55 始终被占用（原因未知），改用 clientId 99
- `nest_asyncio.apply()` 在这个场景无效，因为问题不是"嵌套"而是"跨线程"
- `ib_insync/util.py` 的 `getLoop()` 为每个调用线程创建新 loop，不是共享的
- 直接在主线程调用 `ib.reqContractDetails()` 正常（因为是在创建 ib 的线程）

## 待修复

`TypeError: A coroutine object is required` 错误说明传入 `_run_ib_async` 的不是协程。需要检查：
1. `ib.reqContractDetailsAsync()` 返回的确实是 Awaitable
2. `_run_ib_async` 的 callable 检测逻辑是否正确
3. 确认 ib._loop 是否正确设置