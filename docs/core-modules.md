# 核心模块约定

## kanban/

Streamlit 多页面应用主模块。

### pages/
- `1_dashboard.py` - 仪表盘页面（行情展示、快速操作）
- `2_new_task.py` - 新建任务页面
- `3_task_detail.py` - 任务详情页面
- `4_library.py` - 策略库页面

### app.py
- Streamlit 主入口
- 页面路由和导航

## okx_client/

OKX API 客户端模块。

### 导出函数/类
- `OKXClient` - 主要客户端类
- `get_ticker(symbol)` - 获取行情
- `place_order(symbol, side, amount)` - 下单
- `get_account()` - 获取账户信息

### 约定
- API 密钥从 `config.py` 读取
- 支持构造函数注入（便于测试）
- HTTP 状态码检查：4xx/5xx → 抛异常

## account/

账户管理模块。

### 导出函数
- `get_balance()` - 获取余额
- `get_positions()` - 获取持仓
- `get_history()` - 获取历史记录

## orders/

订单处理模块。

### 导出函数
- `place_order(symbol, side, amount, price)` - 下单
- `cancel_order(order_id)` - 撤单
- `get_orders(status=None)` - 查询订单
- `get_order_detail(order_id)` - 订单详情

### 约定
- 当前缺少单元测试（需补充）

## notify/

通知和 webhook 模块。

### 导出函数
- `send_dingtalk_alert(message)` - 发送钉钉通知
- `send_feishu_alert(message)` - 发送飞书通知
- `webhook_bridge.py` - Webhook 桥接服务

### 注意事项
- `webhook_bridge.py:331` 存在未定义 `get_z120_status()` 问题（P0 待修复）

## z120_monitor/

监控模块。

### 导出函数
- `check_market_status()` - 检查市场状态
- `detect_divergence()` - 检测背离信号
- `calculate_resonance()` - 计算共振度

### 约定
- 使用 YAML 配置文件 (`instruments.yaml`)
- 测试文件：`test_backtest.py`
