# TV跨周期分析命令集成计划

## TL;DR

> **Quick Summary**: 在 `/tv` 命令中集成 TradingView 跨周期分析，从 CDP 读取 M30/M5/M1 数据，为每个品种生成独立的飞书友好报告（含颜色标注）
>
> **Deliverables**:
> - `run_tv_cross_timeframe_analysis()` 函数
> - `/tv` 命令注册到 COMMANDS
> - 多品种支持，每品种独立报告块
>
> **Estimated Effort**: Short
> **Parallel Execution**: NO - 顺序实现
> **Critical Path**: 创建函数 → 注册命令 → 测试验证

---

## Context

### Interview Summary
**Key Discussions**:
- 复用 `kanban/src/tv.py` 的 `get_all_tv_indicators()` 函数
- 多品种支持，但每品种独立展示（飞书手机屏幕宽度限制）
- 飞书格式：单品种详细报告，不合并表格
- 颜色标注：🔴=极端，🟡=中等

**Research Findings**:
- `get_all_tv_indicators(timeframe="30m")` 返回 `{"tabs": [...], "tab_count": N, "mode": "multi_window", "timeframe": "30m"}`
- 每个 tab 包含: symbol, exchange, description, quote{close}, studies[]
- Studies 中有 Z-Score、长期相关性 等指标
- `webhook_bridge.py` 已有 `send_feishu()` 和 COMMANDS 字典

---

## Work Objectives

### Core Objective
在 webhook_bridge.py 中新增 `/tv` 命令，从 TradingView CDP 获取 M30/M5/M1 数据并生成飞书友好报告

### Concrete Deliverables
- [ ] `run_tv_cross_timeframe_analysis()` 函数（位于 webhook_bridge.py）
- [ ] `/tv` 命令注册到 COMMANDS 字典
- [ ] 多品种循环，每品种独立报告块
- [ ] 飞书消息发送

### Definition of Done
- [ ] `/tv` 命令响应并发送飞书消息
- [ ] 消息包含所有品种的 M30/M5/M1 Z-Score 和相关性
- [ ] 颜色标注正确（🔴🟡）
- [ ] 单品种独立格式，不合并表格

### Must Have
- 调用 `get_all_tv_indicators()` 获取数据
- 处理 TV 连接超时/失败（优雅降级）
- 每品种独立报告块

### Must NOT Have
- 不修改 `kanban/src/tv.py` 或 `kanban/pages/5_cross_timeframe.py`
- 不合并多品种到单表格
- 不超过飞书消息长度限制（约4000字符）

---

## Technical Approach

### 数据流
```
/tv 命令 → get_all_tv_indicators("30m")
        → get_all_tv_indicators("5m")
        → get_all_tv_indicators("1m")
        → 聚合到 symbol_map
        → 遍历每个品种格式化报告
        → send_feishu(combined_message)
```

### 时间周期
固定为 M30/M5/M1（不作为可配置参数）

### 数据项（每个时间周期）
| 指标 | 说明 |
|------|------|
| Z-Score | Z-Score 值 |
| 长期相关性 | 长期相关性 (corr) |
| 短期相关性 | 短期相关性 (短期相关性) |

### 颜色阈值
| 指标 | 🔴 红底白字 | 🟡 黄底黑字 |
|------|-----------|-----------|
| Z-Score | \|Z\| ≥ 3 | \|Z\| ≥ 2 |
| 相关性 | corr < -0.5 | corr < 0 |

### 报告格式（单品种）
```
━━━ USATECM2026 (NASDAQ 100 CFD) ━━━
💰 价格: 27782.75

📊 M30 | Z: 1.29 | 长相关: 0.65 | 短相关: -0.52
📊 M5  | Z: 0.84 | 长相关: -0.19 | 短相关: xxx
📊 M1  | Z: -0.74 | 长相关: 0.98 | 短相关: xxx

⚡ 信号: ⚪ 中性
📝 依据: 多周期方向不一致
```

### 错误处理
- TV 连接失败 → 返回 "❌ TradingView 数据不可用，请检查 CDP 连接"
- 无数据 → 返回 "⚠️ 未获取到任何图表数据"

### 消息长度控制
- 单品种报告约 200-300 字符
- 超过 10 个品种时截断并提示 "（共 N 个品种，显示前10个）"

---

## Implementation Steps

### Task 1: 创建 `run_tv_cross_timeframe_analysis()` 函数

**What to do**:
1. 在 `webhook_bridge.py` 顶部 `sys.path` 添加 `kanban` 目录
2. 创建函数 `run_tv_cross_timeframe_analysis()`:
   - 调用 `get_all_tv_indicators("30m")`, `get_all_tv_indicators("5m")`, `get_all_tv_indicators("1m")`
   - 聚合到 `symbol_map`（按 symbol 分组）
   - 遍历每个 symbol，调用 `format_symbol_report()` 生成报告
   - 调用 `send_feishu()` 发送
3. 创建辅助函数 `format_symbol_report(symbol, m30_data, m5_data, m1_data)`:
   - 解析 Z-Score 和相关性
   - 应用颜色标注
   - 返回格式化字符串

**References**:
- `kanban/src/tv.py:get_all_tv_indicators()` - 数据源
- `kanban/pages/5_cross_timeframe.py:parse_float()` - 数字解析
- `kanban/pages/5_cross_timeframe.py:evaluate_signal()` - 信号评估逻辑

**Acceptance Criteria**:
- [ ] 函数存在且语法正确
- [ ] import 语句正确添加

### Task 2: 注册 `/tv` 命令

**What to do**:
在 `COMMANDS` 字典中添加:
```python
"tv": lambda: run_tv_cross_timeframe_analysis(),
```

**References**:
- `notify/webhook_bridge.py:824-850` - COMMANDS 字典位置

**Acceptance Criteria**:
- [ ] "tv" 键存在于 COMMANDS 中
- [ ] 命令可被 `feishu_webhook` 路由识别

### Task 3: 验证测试

**QA Scenarios**:

```
Scenario: /tv 命令正常返回数据
  Tool: Bash (curl)
  Preconditions: TradingView CDP 可连接
  Steps:
    1. curl -X POST http://localhost:5002/feishu-webhook \
       -H "Content-Type: application/json" \
       -d '{"message": {"content": "{\"text\": \"/tv\"}", "chat_id": "oc_xxx"}}'
  Expected Result: 飞书收到消息，包含跨周期分析数据
  Evidence: 飞书群消息

Scenario: TV 连接失败时优雅处理
  Tool: Bash (curl)
  Preconditions: 停止 TradingView CDP
  Steps:
    1. curl -X POST http://localhost:5002/feishu-webhook \
       -H "Content-Type: application/json" \
       -d '{"message": {"content": "{\"text\": \"/tv\"}", "chat_id": "oc_xxx"}}'
  Expected Result: 飞书收到错误提示，不是500
  Evidence: 飞书群消息
```

---

## Final Verification Wave

- [x] F1: Plan Compliance Audit — 验证所有 Must Have 存在，Must NOT Have 不存在
- [x] F2: Code Quality Review — `python3 -m py_compile notify/webhook_bridge.py`
- [x] F3: Real Manual QA — 发送 /tv 命令，验证飞书消息
- [x] F4: Scope Fidelity Check — 验证仅修改了目标文件

---

## Commit Strategy

- Commit: YES ✅
- Message: `FEAT(notify): add /tv command for TradingView cross-timeframe analysis`
- Files: `notify/webhook_bridge.py`

---

## Success Criteria

### Verification Commands
```bash
# 语法检查
python3 -m py_compile notify/webhook_bridge.py

# 发送 /tv 命令测试
curl -X POST http://localhost:5002/feishu-webhook \
  -H "Content-Type: application/json" \
  -d '{"message": {"content": "{\"text\": \"/tv\"}", "chat_id": "oc_c662ae6c37140f6daab19c0de30dbfd3"}}'
```

### Final Checklist
- [x] `run_tv_cross_timeframe_analysis()` 函数已创建
- [x] `/tv` 命令已注册
- [x] 多品种独立报告格式
- [x] 颜色标注正确
- [x] 错误处理优雅
