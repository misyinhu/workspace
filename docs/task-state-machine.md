# 任务状态机

## 状态流转

```
pending → analyzing → pending_review
                     ↓ (审核通过)
                   generating → pending_review
                                   ↓ (审核通过)
                                         completed

任何阶段审核驳回 → rejected → (需新建任务)
```

## 状态说明

| 状态 | 含义 |
|------|------|
| `pending` | 待处理（新建或失败重试） |
| `analyzing` | 行情分析/信号扫描中 |
| `pending_review` | 等待审核（信号方案） |
| `generating` | 执行交易/推送信号中 |
| `completed` | 已完成 |
| `rejected` | 人工审核驳回（仅人工用） |

## 重要规则

- **失败 → `pending`**：抓取失败、分析失败、执行失败都改为 `pending`，允许重试
- **`rejected` 仅人工用**：只有用户在审核页面点"驳回"才设为 `rejected`
- **超时不改状态**：网络超时等临时错误不改状态，保持当前状态

## 页面流转

```
1_dashboard (仪表盘)
    ↓ 点击"新建任务"
2_new_task (新建任务)
    ↓ 填写完成
3_task_detail (任务详情/审核)
    ↓ 审核通过
4_library (策略库/历史)
```
