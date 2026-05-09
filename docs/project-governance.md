# 项目治理规则

> 项目经理（Sisyphus）与 Dev（worker session）的协作边界。

## 文件更新权限

| 文件 | 更新权 | 说明 |
|------|--------|------|
| **AGENTS.md** | **仅项目经理** | 记录"哪个 change、下一个动作是什么"。Dev 禁止修改。 |
| **`openspec/*/tasks.md`** | Dev + 项目经理 | Dev 完成 checkbox 后自己打勾 `[ ]` → `[x]`。 |
| **`docs/verified-facts.md`** | **仅项目经理** | 已验证事实（API 端点、扫描行为等）。Dev 不碰。 |
| **`/context-save` 文件** | Dev | Dev 被中断前自己保存进度。 |
| **项目代码（`kanban/`, `okx_client/` 等）** | Dev | Dev 自由实现，项目经理不干预具体实现。 |

## 铁律

1. **AGENTS.md 单一责任人**：任何时候，只有一个 agent（项目经理）更新 `AGENTS.md` 的 "Current Work" 区块。禁止多个 agent 同时修改。

2. **Dev 不碰 AGENTS.md**：Dev 启动时读 `AGENTS.md` 知道该做什么，但不修改它。

3. **已验证事实不可覆盖**：`docs/verified-facts.md` 记录的是测过的事实（如 `api.okx.com/api/v5` 是对的）。Dev 不能"觉得自己对了"就改。

4. **冲突处理**：如果 Dev session 错误地修改了 `AGENTS.md`，项目经理下次启动时发现并回退。

## Dev 正确工作流

```
Dev session 启动时：
1. 读 AGENTS.md（知道当前 change 和下一个任务）
2. 读 openspec/*/tasks.md（找第一个 [ ]）
3. 实现代码
4. 完成 checkbox → 用 Edit 工具更新 tasks.md（[ ] → [x]）
5. 被中断前 → /context-save <task-name>-progress
   （⚠️ 不碰 AGENTS.md）
```

## 项目经理（我）的工作流

```
1. 定期检查 tasks.md 完成进度
2. 大阶段变更（如 M1 → M2）→ 更新 AGENTS.md "Current Work" 区块
3. 发现新验证事实 → 更新 docs/verified-facts.md
4. 发现 Dev 错误修改 AGENTS.md → 回退并通知
```

## 违规示例

| 行为 | 处理 |
|------|------|
| Dev 修改 AGENTS.md 的 Current Work | 项目经理发现后回退，下次 session 告知 Dev |
| Dev 把 `api.okx.com` 改成 `.io` | 项目经理回退，事实在 verified-facts.md 里，Dev 应该先查 |
| 多个 Dev 同时改 tasks.md | 没问题，tasks.md 是 checkbox 列表，git merge 会处理 |

---

## PMO 治理框架参考

本项目遵循 PMO 治理框架 v2.1。详细定义见：

| 文档 | 位置 | 说明 |
|------|------|------|
| **PMO-GOVERNANCE.md** | ../../pmo/openspec/specs/PMO-GOVERNANCE.md | 全局治理框架 |
| **role-pm.md** | ../../../../pmo/docs/role-pm.md | PM 职责与工作流程 |
| **role-dev.md** | ../../../../pmo/docs/role-dev.md | DEV 职责与工作流程 |
| **role-qa.md** | ../../../../pmo/docs/role-qa.md | QA 职责与工作流程 |
| **role-pmo.md** | ../../../../pmo/docs/role-pmo.md | PMO 职责与调度流程 |
| **dispatch-protocol.md** | ../../../../pmo/docs/dispatch-protocol.md | task() dispatch 标准流程 |
| **test-report-template.md** | ../../../../pmo/docs/test-report-template.md | 测试报告格式 |

### Session ID（扁平化联系）

| 角色 | Session ID |
|------|-----------|
| 交易团队 PM | `ses_23d5abc84ffesCO0xFUvHXeuuo` |
| 交易团队 QA | `ses_1f4338ab8ffeFvozDggSH4JnUy` |
| 交易团队 DEV | `ses_31ae5bce4ffeMF6vtcW7Mqll6Z` |


### 项目级文档清单

| 文档 | 位置 | 说明 |
|------|------|------|
| tasks.md | ../openspec/changes/trading/tasks.md | 任务清单 |
| verified-facts.md | ./verified-facts.md | 验收事实 |
| test-cases.md | ./test-cases.md | 测试用例 |
| test-reports/ | ./test-reports/ | 归档测试报告 |
| code-style.md | ./code-style.md | 代码规范 |
| project-governance.md | ./project-governance.md | 项目治理 |
