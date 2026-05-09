# verified-facts

> 本文件是 QA 与 DEV 的唯一事实源。所有验证结果必须记录在此。
> 
> **参考**：PMO 治理框架定义见 [pmo/docs/role-qa.md](../../pmo/docs/role-qa.md)

---

## 验收事实

> 本部分记录 trading 项目功能验收的事实记录。

### Feature 1: OKX 行情对接

| # | 事实 | 验证方式 | 状态 | 验证时间 |
|---|------|---------|------|---------|

### Feature 2: IB 交易执行

| # | 事实 | 验证方式 | 状态 | 验证时间 |
|---|------|---------|------|---------|

### Feature 3: TradingView Webhook

| # | 事实 | 验证方式 | 状态 | 验证时间 |
|---|------|---------|------|---------|

---

## Issue 清单

| # | 标题 | 严重性 | 状态 | 发现时间 | 关闭时间 |
|---|------|--------|------|---------|---------|
| 1 | `get_z120_status()` 未定义 | P0 | Open | 2026-05-05 | - |
| 2 | `color` 变量未定义（3_screen.py:187） | P0 | Open | 2026-05-05 | - |
| 3 | 重复字典键 `"黄金"`（nl_parser.py:132） | P0 | Open | 2026-05-05 | - |

---

## Issue #1

**标题**：`get_z120_status()` 未定义
**严重性**：P0
**状态**：Open
**发现者**：DEV
**发现时间**：2026-05-05
**描述**：代码引用了未定义的函数
**修复方案**：实现 `get_z120_status()` 函数

---

## Issue #2

**标题**：`color` 变量未定义（3_screen.py:187）
**严重性**：P0
**状态**：Open
**发现者**：DEV
**发现时间**：2026-05-05
**描述**：第 187 行引用了未定义的 `color` 变量
**修复方案**：定义 `color` 变量或修正引用

---

## Issue #3

**标题**：重复字典键 `"黄金"`（nl_parser.py:132）
**严重性**：P0
**状态**：Open
**发现者**：DEV
**发现时间**：2026-05-05
**描述**：字典中有重复的键 `"黄金"`
**修复方案**：合并或移除重复键

---

## 技术事实（项目特定）

> 以下是 trading 项目特定的技术事实，与 PMO 验收框架分开记录。

### API 端点

- ✅ OKX API: `https://api.okx.com/api/v5` — 验证于 2026-05-05
  - 行情端点：`/market/ticker`
  - 下单端点：`/trade/order`
  - 账户端点：`/account/balance`
- ✅ Interactive Brokers: `localhost:4001` (TWS/Gateway) — 验证于 2026-05-05
- ✅ TradingView Webhook: `https://tv.alert.feed` — 验证于 2026-05-05
- ✅ 钉钉 Webhook: `https://oapi.dingtalk.com/robot/send` — 验证于 2026-05-05

### 扫描行为

- ✅ OKX 请求失败 → 抛异常（不能静默返回错误页面）
- ✅ IB 连接超时 → 保持当前状态，不改状态机
- ✅ TradingView 推送 → 先验证签名，再处理信号

### 状态机

- ✅ 失败路径（分析/执行失败）→ `pending`（可重试）
- ✅ `rejected` 仅用于人工审核拒绝（G1/G4 驳回）
- ✅ 超时等临时错误不改状态，保持当前状态

### 持久化

- ✅ 任务持久化到 `data/tasks.json`（非 session_state）
- ✅ 所有页面（dashboard/new_task/task_detail/library）都读这个文件
- ✅ 新任务失败 → 先 `add_task()` 再 `st.rerun()`（页面不回退）

### 配置文件

- ✅ `config.py` 包含硬编码密钥 — 验证于 2026-05-05 用户确认
- ✅ `data/` 目录已加入 `.gitignore`
- ✅ Python 3.13 环境 — 验证于 2026-05-05

---

## 已修复的坑

- ❌ ~~裸 except 吞噬错误~~ → 改为具体异常捕获

---

## 更新规则

1. **QA 验证通过** → QA 更新对应项状态为 ✅
2. **QA 发现 Issue** → 在 Issue 清单创建条目
3. **Issue 修复** → DEV 更新状态为 `Pending Re-test`，QA 验证通过后更新为 `Closed`
4. **技术事实** → 任何角色发现新事实可更新

---

## PMO 治理框架参考

| 文档 | 位置 |
|------|------|
| PMO 治理架构 | ../../pmo/openspec/specs/PMO-GOVERNANCE.md |
| PM 角色手册 | ../../pmo/docs/role-pm.md |
| DEV 角色手册 | ../../pmo/docs/role-dev.md |
| QA 角色手册 | ../../pmo/docs/role-qa.md |
| PMO 角色手册 | ../../pmo/docs/role-pmo.md |
| Dispatch 协议 | ../../pmo/docs/dispatch-protocol.md |
| 测试报告模板 | ../../pmo/docs/test-report-template.md |

### OKX SDK 2.x 兼容性问题（2026-05-09）

| # | 事实 | 验证方式 | 状态 |
|---|------|---------|------|
| 1 | SDK 2.x 导入路径是 `okx.api.Account/Trade/Market`（不是 `okx.Account/Trade/Market`） | 本地测试 | ✅ 已验证 |
| 2 | SDK 2.x `AccountAPI.__init__()` 不接受 `proxies` 参数 | winclaw 测试 | ✅ 已验证 |
| 3 | 永续合约需要 `posSide`（long/short），现货不需要 | winclaw 测试 | ✅ 已验证 |
| 4 | 模拟盘 flag="1"，实盘 flag="2" | okx.yaml 配置 | ✅ 已验证 |
| 5 | `okx_client/config.yaml` 会覆盖 `config/okx.yaml` | winclaw 实测 | ⚠️ 需删除 |

### OKX 交易对模式识别

| 交易对格式 | 类型 | margin_mode | posSide |
|-----------|------|-------------|---------|
| `DOGE-USDT` | 现货 | cash | 不传 |
| `DOGE-USDT-SWAP` | 永续合约 | cross | long/short |
| `ETH-USDT-SWAP` | 永续合约 | cross | long/short |
