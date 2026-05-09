# 测试用例（自动化友好格式）

> 本文件采用 Gherkin 格式，支持 QA 手工执行或 DEV 转换为自动化测试。
> **格式**：Given-When-Then，明确 Pre-conditions 和 Schema 断言
> **来源**：proposal.md + design.md + tasks.md

---

## 全局 Schema 字典（Contract Repository）

所有 TC 引用的标准对象定义于此。重复字段不再在各 TC 中定义。

### 1. OrderObject（OKX 下单响应）

```json
{
  "code": "string (0=成功, 非0=失败)",
  "msg": "string (错误描述，成功时为空)",
  "data": [
    {
      "ordId": "string (订单唯一ID，正整数)",
      "clOrdId": "string (客户端自定义ID，可选)"
    }
  ]
}
```

**Schema 引用**: `$OrderObject`  
**验证规则**:
- `$.code == "0"` 表示成功
- `$.data[0].ordId` 正则匹配 `^[0-9]+$`

---

### 2. SignalPayload（Webhook 输入）

```json
{
  "action": "enum['buy', 'sell', 'close']",
  "symbol": "string (如 'BTC-USDT', 'GC')",
  "qty": "number (>0)",
  "order_type": "string (default: 'market')"
}
```

**Schema 引用**: `$SignalPayload`  
**验证规则**:
- `$.action` 枚举值: buy/sell/close
- `$.symbol` 非空字符串
- `$.qty` > 0

---

### 3. WebhookResponse（/tv-webhook 标准响应）

```json
{
  "status": "string (ok/error)",
  "order": "$OrderObject | {error: string}",
  "config": {
    "app_id": "boolean",
    "conversation_id": "boolean",
    "query_only": "boolean"
  }
}
```

**Schema 引用**: `$WebhookResponse`  
**验证规则**:
- `$.status` == "ok" 或 "error"
- 如果 `$.status == "ok"`，则 `$.order` 符合 `$OrderObject`
- 如果 `$.status == "error"`，则 `$.order.error` 为非空字符串

---

### 4. FinancialNewsItem（新闻条目）

```json
{
  "title": "string",
  "summary": "string (可选)",
  "published": "string (ISO8601 日期)",
  "source": "string",
  "url": "string (可选)"
}
```

**Schema 引用**: `$FinancialNewsItem`

---

### 5. SentimentPost（情绪帖子）

```json
{
  "title": "string",
  "author": "string",
  "upvotes": "number",
  "subreddit": "string",
  "sentiment": "enum['bullish', 'bearish', 'neutral']",
  "sentiment_score": "number (0.0-1.0)"
}
```

**Schema 引用**: `$SentimentPost`

---

### 6. MarketAnalysisReport（市场分析报告）

```json
{
  "conclusion": "string (原因推断)",
  "confidence": "number (0.0-1.0)",
  "evidence": {
    "news": ["string (新闻标题)"],
    "sentiment": "string (情绪摘要)",
    "technical": "string (技术面摘要)"
  },
  "related_links": ["string (URL)"]
}
```

**Schema 引用**: `$MarketAnalysisReport`

---

## 一、Webhook 服务

### WH-001: 健康检查端点

```gherkin
Scenario: 健康检查返回正常状态
  Given 服务运行在 {host}:5002
  When 用户发送 GET 请求至 "/health"
  Then HTTP 状态码 = 200
  And Response Body 应符合 $WebhookResponse
  And $.status = "ok"
  And $.config.app_id = true
  And $.config.conversation_id = true
```

---

### WH-101: TradingView 买入信号处理

**Pre-conditions**:
- OKX 模拟盘账户余额 ≥ 10 USDT
- OKX API Key 有效（未过期/未吊销）
- 网络代理已配置（127.0.0.1:7890）
- `config/okx.yaml` flag="sim"

```gherkin
Scenario: TV webhook 处理买入信号 (WH-101)
  Given OKX 模拟盘 API 已就绪
  And 账户持有 >= 10 USDT
  When 接收到 POST 请求至 "/tv-webhook"
  And Headers: Content-Type: application/json
  And Payload 应符合 $SignalPayload
  And Payload = {"action": "buy", "symbol": "DOGE-USDT", "exchange": "OKX", "qty": 1, "order_type": "market"}
  Then HTTP 状态码 = 200
  And Response Body 应符合 $WebhookResponse
  And $.status = "ok"
  And $.order.code = "0"
  And $.order.data[0].ordId 正则匹配 "^[0-9]+$"

Scenario: OKX 下单失败（余额不足）
  Given OKX 账户余额 < 1 USDT
  When POST "/tv-webhook" Payload = {"action": "buy", "symbol": "BTC-USDT", "qty": 1}
  Then HTTP 200
  And Response Body 应符合 $WebhookResponse
  And $.order.error 匹配 "余额|insufficient|balance"

Scenario: OKX API Key 无效
  Given config/okx.yaml 使用过期/吊销的 API Key
  When POST "/tv-webhook" Payload = {"action": "buy", "symbol": "BTC-USDT", "qty": 1}
  Then HTTP 200
  And $.order.error 匹配 "401|APIKey|invalid|environment"

Negative Testing:
  When POST "/tv-webhook" Payload 为非 JSON 格式
  Then HTTP 状态码 >= 400

  When POST "/tv-webhook" Payload 缺少 action 字段
  Then $.status = "error"

  When POST "/tv-webhook" Payload qty = 0
  Then $.status = "error"
```

---

### WH-102: TradingView 卖出信号处理

```gherkin
Scenario: TV webhook 处理卖出信号
  Given 持有 DOGE-USDT >= 1
  When POST "/tv-webhook" Payload = {"action": "sell", "symbol": "DOGE-USDT", "qty": 1}
  Then HTTP 200
  And Response Body 应符合 $WebhookResponse
  And $.order.code = "0"

Scenario: 卖出但无持仓
  Given 账户不持有 DOGE-USDT
  When POST "/tv-webhook" Payload = {"action": "sell", "symbol": "DOGE-USDT", "qty": 1}
  Then HTTP 200
  And $.order.error 匹配 "余额不足|insufficient"

Scenario: 重复信号去重
  Given 系统已记录 signal_hash = SHA256(action+symbol+qty)
  When 在 30 秒内 POST 相同信号两次
  Then 第一次: $.order.code = "0"
  And 第二次: $.order.error 匹配 "duplicate|already|重复" 或 $.order.code = "0" 但实际未下单
```

---

### WH-201: 飞书命令解析

**Pre-conditions**: 飞书 Webhook 服务运行，NL 解析器正常

```gherkin
Scenario: 解析"买入1手GC"
  Given 飞书 Webhook 服务运行
  When POST "/feishu-webhook" Payload = {"message": {"content": "买入1手GC"}}
  Then NL 解析结果:
    - action = "buy"
    - symbol = "GC"
    - quantity = 1
    - sec_type = "FUT"

Scenario: 解析"卖空2手NQ"
  When POST "/feishu-webhook" Payload = {"message": {"content": "卖空2手NQ"}}
  Then 解析结果: action="sell", symbol="NQ", quantity=2

Scenario: 解析"平仓GC"
  When POST "/feishu-webhook" Payload = {"message": {"content": "平仓GC"}}
  Then 解析结果: action="close", symbol="GC"

Scenario: 解析"查看持仓"
  When POST "/feishu-webhook" Payload = {"message": {"content": "查看持仓"}}
  Then 解析结果: action="query"
```

---

### WH-301: 成交通知

**Pre-conditions**: 飞书 Webhook URL 已配置，exec_id 去重机制已实现

```gherkin
Scenario: 订单成交后发送飞书通知
  Given 订单已提交且配置了 execDetails 回调
  When 订单成交（fill event）
  Then 飞书收到 HTTP POST 请求
  And 请求体包含: symbol, direction(买入/卖出), quantity, price

Scenario: exec_id 去重
  Given 同一 exec_id 触发两次回调
  When 第二次回调到达
  Then 飞书收到通知 <= 1 次（去重生效）

Scenario: 通知格式验证
  Given 飞书收到成交通知
  Then 通知包含字段: contract(合约名), side(方向), size(数量), price(价格)
```

---

## 二、Kanban 导航

### KB-001 ~ KB-008: 页面切换

```gherkin
Scenario: 侧边栏显示所有页面
  Given 用户已登录 Kanban APP
  When 页面加载完成
  Then 侧边栏显示页面链接:
    - 新闻事件中心 (0_news_center.py)
    - 警报中心 (1_alerts.py)
    - 市场扫描 (2_market_scan.py)
    - 三重滤网 (3_three_screen.py)
    - 多周期共振 (4_resonance.py)
    - 跨周期分析 (5_cross_timeframe.py)
    - 市场分析 (6_market_agent.py)
  And 每个链接可点击跳转

Scenario: 点击页面链接后 URL 正确
  Given 用户在 Kanban 主页面
  When 点击 "新闻事件中心"
  Then URL 包含 /0_news_center.py 或等效路由
  And 页面内容为新闻事件中心

# KB-003 到 KB-008 同理
```

---

## 三、新闻事件中心（0_news_center.py）

### NC-001: 日期筛选

**Pre-conditions**: tv_mcp_financial_news 可访问，返回的数据包含 ISO8601 日期

```gherkin
Scenario: 默认日期为今天
  When 用户打开新闻事件中心页面
  Then 开始日期 input 默认 = 今天 (date.today())
  And 结束日期 input 默认 = 今天

Scenario: 日期范围筛选
  Given 有 2024-01-01 至 2024-01-31 的新闻数据
  When 用户设置开始日期 = 2024-01-15，结束日期 = 2024-01-20
  Then 仅显示 2024-01-15 <= published <= 2024-01-20 的新闻

Negative Testing:
  When 开始日期 > 结束日期
  Then 显示错误提示 OR 自动交换日期

  When 日期格式无效
  Then 显示错误提示
```

---

### NC-101: 分类筛选

```gherkin
Scenario: 选择"全部"分类
  When 用户选择分类 = "all"
  Then 调用 tv_financial_news(category="all")
  And 显示所有分类新闻

Scenario: 选择"加密货币"分类
  When 用户选择分类 = "crypto"
  Then 调用 tv_financial_news(category="crypto")
  And 仅显示加密货币新闻

Scenario: 选择"股票"分类
  When 用户选择分类 = "stocks"
  Then 调用 tv_financial_news(category="stocks")
```

---

### NC-201: 新闻数量滑块

```gherkin
Scenario: 滑块范围 5-30
  Given 滑块配置 min=5, max=30, default=10
  When 用户设置滑块值 = 5
  Then 调用 tv_financial_news(limit=5)

  When 设置滑块值 = 30
  Then 调用 tv_financial_news(limit=30)

Negative Testing:
  When 输入值 < 5（如 0 或 -1）
  Then 使用最小值 5 或显示错误

  When 输入值 > 30（如 999）
  Then 使用最大值 30 或显示错误
```

---

### NC-301: 财经新闻 Tab

**Pre-conditions**: tv_financial_news 返回非空 items 数组

```gherkin
Scenario: 新闻加载显示
  When 用户切换到"财经新闻" Tab
  Then 显示 spinner "加载财经新闻..."
  And spinner 消失后显示新闻列表
  And 每条新闻标题截断至 80 字符

Scenario: 点击新闻展开详情
  Given 新闻列表已显示
  When 用户点击某条新闻的 expander
  Then 展开内容包含:
    - published (ISO8601，前16字符显示)
    - source (来源)
    - summary (前300字符或 title)

Scenario: 无新闻数据
  Given tv_financial_news 返回空 items 或 error
  Then 显示 "暂无新闻数据"
```

---

### NC-401: 市场情绪 Tab

**Pre-conditions**: tv_market_sentiment 返回 top_posts 数组

```gherkin
Scenario: 默认 Symbol 根据分类
  Given category = "crypto"
  When 切换到"市场情绪" Tab
  Then Symbol input 默认值 = "BTC"

  Given category = "stocks"
  Then 默认值 = "AAPL"

Scenario: 自定义 Symbol 查询
  When 用户输入 "ETH" 并提交
  Then 调用 tv_market_sentiment(symbol="ETH", category="all")
  And 显示 ETH 的情绪数据

Scenario: 情绪分数显示
  Given tv_market_sentiment 返回数据
  Then 显示:
    - sentiment_label: "Bullish" / "Bearish" / "Neutral"
    - sentiment_score: 0.00-1.00
    - posts_analyzed: 已分析帖子数

Scenario: 帖子列表格式
  Then 每个 top_post 包含字段:
    - title
    - author
    - upvotes (数值)
    - subreddit
    - sentiment (bullish 显示 🟢，bearish 显示 🔴)
```

---

## 四、警报中心（1_alerts.py）

### AL-001: 周期选择与连接检测

```gherkin
Scenario: 默认周期为 15s
  When 页面加载
  Then 默认选择 "15s" 周期
  And 调用 get_all_tv_indicators(timeframe="15s")

Scenario: 切换周期
  When 用户选择 "1m"
  Then 调用 get_all_tv_indicators(timeframe="1m")
  And 页面数据更新为 1m 周期

Scenario: 所有周期选项可用
  Then 可选周期: 1m, 5m, 15s, 30m, 3h

Scenario: TV 连接失败
  Given TV CDP 不可达 (TV_HOST:TV_PORT)
  When 页面加载
  Then 显示警告: "无法连接到 TradingView CDP"
  And 不继续加载后续数据

Scenario: 无布局提示
  Given TradingView 未打开任何图表布局
  When 页面加载
  Then 显示警告: "⚠️ 未扫描到任何图表，请在 TradingView 中打开布局"
```

---

### AL-201: 警报检测逻辑

```gherkin
Scenario: Z-Score >= 2 触发警报
  Given 某指标的 Z-Score 值 = 2.5
  When 警报检测执行
  Then 添加到警报列表
  And 显示 🟡 图标

Scenario: Z-Score >= 3 高危标注
  Given Z-Score = 3.5
  Then 显示 🔴 图标

Scenario: 短期相关性 < 0.2
  Given 短期相关性 = 0.15
  Then 添加到警报列表

Scenario: 警报计数显示
  Given 有 N 条活跃警报
  Then 页面显示警报数量 N
```

---

### AL-301: 指标详情展开

```gherkin
Scenario: Tab expander 显示价格数据
  Given Tab 有 quote 数据
  When 用户点击 Tab expander
  Then 显示 4 个 metric:
    - 最新价 (close, 2位小数)
    - 开盘 (open)
    - 最高 (high)
    - 最低 (low)

Scenario: 无 quote 数据
  Given Tab 的 quote = null 或空
  Then 不显示 metric 或显示 N/A
```

---

## 五、市场扫描（2_market_scan.py）

### MS-001: 扫描类型与参数

```gherkin
Scenario: 显示 5 种扫描类型
  Then 扫描类型选项:
    - volume_breakout: 交易量突破
    - bollinger: 布林带分析
    - trending: 趋势分析
    - consecutive: 连续K线
    - multi_changes: 多周期变化

Scenario: 选择类型显示对应参数
  When 选择 "交易量突破"
  Then 显示参数: timeframe(select), volume_multiplier(1.5-5.0), price_change_min(1.0-10.0), limit(5-50)

  When 选择 "布林带分析"
  Then 显示参数: timeframe, bb_period(10-30), bb_std(1.5-3.0), limit
```

---

### MS-101: 市场选择

```gherkin
Scenario: 常用品种开关
  When 用户勾选 "常用品种"
  Then 使用 get_common_symbols() 返回的品种列表

  When 取消勾选
  Then 不使用常用品种

Scenario: 交易所多选
  When 勾选 "OKX (加密)"
  Then 参数 exchanges 包含 "okx"

  When 同时勾选 "OKX" 和 "上交所 (A股)"
  Then exchanges = ["okx", "sse"]
```

---

### MS-301: 扫描执行

```gherkin
Scenario: 点击开始扫描
  Given 参数已配置（类型、交易所等）
  When 点击 "🚀 开始扫描"
  Then 显示 spinner "扫描中..."
  And 调用 POST /api/scan/{scanner_type}
  Then spinner 消失
  And 显示扫描结果（表格或卡片）

Scenario: 扫描无结果
  Given 没有满足条件的标的
  Then 显示 "暂无满足条件的结果"

Scenario: Quant Core 不可用
  Given QUANT_CORE_URL 不可达
  Then 显示连接错误信息
```

---

## 六、三重滤网（3_three_screen.py）

### TS-201: 扫描与信号显示

**Pre-conditions**: Quant Core 可访问，历史K线数据存在

```gherkin
Scenario: 点击开始扫描
  Given 参数已配置
  When 点击 "🚀 开始扫描"
  Then 调用 POST /api/scan/three-screen
  And 显示 spinner

Scenario: 三重向上买入信号
  Given M30 趋势向上 AND M5 向上 AND M1 确认向上
  Then 显示:
    - 信号文字包含 "做多"
    - 图标为 📈
    - color 变量已定义（非 undefined，P0 修复验证）

Scenario: 三重向下卖出信号
  Given M30 向下 AND M5 向下 AND M1 确认向下
  Then 显示:
    - 信号文字包含 "做空"
    - 图标为 📉

Scenario: 无共振信号
  Then 不显示做多/做空信号
  Or 显示中性状态
```

---

## 七、多周期共振（4_resonance.py）

### RS-001: 图表渲染

```gherkin
Scenario: 有数据时显示图表
  Given TradingView CDP 连接正常
  And 有历史数据
  Then 显示 lightweight-charts
  And 图表包含 MA20 线条

Scenario: 无数据不显示图表
  Given 无历史数据
  Then 不渲染图表区域
```

---

### RS-201: 共振度计算与显示

```gherkin
Scenario: 高共振 >= 75%
  Given 共振度 = 0.8
  Then 显示 "高共振" 标签

Scenario: 中共振 50%-75%
  Given 共振度 = 0.6
  Then 显示 "中共振" 标签

Scenario: 低共振 < 50%
  Given 共振度 = 0.3
  Then 显示 "低共振" 标签

Scenario: 矛盾检测
  Given 多周期方向冲突
  Then 显示矛盾警告
  And 展开详情显示冲突周期
```

---

## 八、跨周期分析（5_cross_timeframe.py）

```gherkin
Scenario: 多周期视图加载
  When 页面加载
  Then 显示多个周期的数据视图
  And 每个周期方向（向上/向下/中性）可见

Scenario: 矛盾周期高亮
  Given 多周期方向冲突
  Then 冲突周期高亮显示
  And 显示矛盾说明
```

---

## 九、市场分析 Agent（6_market_agent.py）

### AG-001: 关键词解析（INDEX_MAP）

```gherkin
Scenario: 解析"纳指"
  Given 用户输入包含 "纳指"
  Then 映射: "纳指" -> symbol="QQQ", exchange="NASDAQ"

Scenario: 解析"道指"
  Then 映射: "道指" -> symbol="DIA", exchange="NYSE"

Scenario: 解析"标普500"
  Then 映射: "标普500" -> symbol="SPY", exchange="NYSE"

Scenario: 解析"油价"
  Then 映射: "油价" -> 相关大宗商品标的

Scenario: 自由文本多关键词
  Given 用户输入: "纳指和道指劈差，可能跟伊朗战争/油价有关"
  Then 提取关键词: ["纳指", "道指", "油价", "伊朗"]
  And 搜索 QQQ, DIA, 原油相关标的
```

---

### AG-101: 并行搜索与报告生成

**Pre-conditions**: tv-mcp 工具可访问，MiniMax API 可用

```gherkin
Scenario: 搜索状态显示
  Given 用户输入市场现象
  When 点击 "🔍 分析" 按钮
  Then 显示 spinner "🔍 分析中..."

Scenario: 并行调用 tv-mcp
  Then 同时调用:
    - tv_financial_news (category, limit)
    - tv_market_sentiment (symbol, category, limit)
    - tv_combined_analysis (symbol, exchange, timeframe)
  And 等待所有完成

Scenario: MiniMax API 调用
  Given 数据汇总完成
  Then 调用 POST https://api.minimax.chat/v1/chat/completions
  And 请求体包含:
    - model: "MiniMax-M2.1"
    - messages: system prompt + user input
    - reasoning: {"type": "disabled"}

Scenario: 报告格式
  Then 返回 MarketAnalysisReport 结构:
    - conclusion: 原因推断 (string)
    - confidence: 置信度 (0.0-1.0)
    - evidence.news: [新闻标题数组]
    - evidence.sentiment: 情绪摘要
    - evidence.technical: 技术面摘要
    - related_links: [URL数组]

Scenario: 无数据降级
  Given 所有 tv-mcp 返回空
  Then 显示 "暂无数据，请尝试其他关键词"

Scenario: API 超时
  Given 30秒内未返回
  Then 显示错误信息
  Or 重试机制触发
```

---

## 十、P0 回归测试

### P0-001 ~ P0-004: 静态分析（自动化检查）

```gherkin
Scenario: P0-001 color 变量已定义（静态检查）
  When 运行 ruff check kanban/pages/3_three_screen.py
  Then 无 NameError 关于 "color"
  And python -m py_compile kanban/pages/3_three_screen.py 成功

Scenario: P0-002 get_z120_status 已移除（静态检查）
  When grep "get_z120_status" notify/webhook_bridge.py
  Then 无匹配结果

Scenario: P0-003 无重复字典键（静态检查）
  When python -c "import ast; ast.parse(open('src/nl_parser.py').read())"
  Then 无 SyntaxWarning

Scenario: P0-004 OKX 下单成功（行为测试）
  Given config/okx.yaml flag="sim"
  And 账户有足够余额
  When POST /tv-webhook Payload = {"action": "buy", "symbol": "DOGE-USDT", "qty": 1}
  Then HTTP 200
  And $.order.code = "0"
  And $.order.data[0].ordId 正则匹配 "^[0-9]+$"
```

---

## 十一、代码质量（自动化检查）

```gherkin
Scenario: Ruff 检查通过
  When 运行 ruff check .
  Then 退出码 = 0
  And 无 ERROR 输出

Scenario: Ruff format 无需修改
  When 运行 ruff format --check .
  Then 退出码 = 0

Scenario: 所有 .py 文件语法正确
  When 运行 python -m py_compile 对所有 .py 文件
  Then 无 SyntaxError
```

---

## 附录：Schema 验证工具推荐

| 工具 | 用途 |
|------|------|
| `jq` | 命令行 JSON 验证 |
| `jsonschema` (Python) | 自动化测试中的 Schema 断言 |
| `chakram` / `supertest` | API 测试 + Schema 验证 |

**示例命令**:
```bash
# jq 验证 OrderObject
curl -s POST /tv-webhook | jq '.order | if .code == "0" then .data[0].ordId | test("^[0-9]+$") else empty end'

# jsonschema 验证
python -c "import jsonschema; jsonschema.validate(instance, schema='$OrderObject')"
```

---

## PMO 治理框架参考

| 文档 | 位置 |
|------|------|
| QA 角色手册 | ../../../../pmo/docs/role-qa.md |
| 测试报告模板 | ../../../../pmo/docs/test-report-template.md |
| verified-facts.md | ./verified-facts.md |
