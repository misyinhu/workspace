# 外汇交易监控系统 - 研究发现

## IB API 外汇持仓查询

### 问题
外汇订单成交后，使用 `ib.positions()` 查询不到持仓。

### 发现
1. **IB API 特性**：外汇持仓可能不显示在标准 `positions()` 调用中
2. **解决方案**：
   - 使用 `ib.portfolio()` 查询
   - 查询特定外汇合约
   - 检查 `accountSummary()` 中的 `FxCashBalance`

### 测试结果
```
Method 1: ib.positions() - 返回 2 个（无外汇）
Method 2: ib.portfolio() - 返回 2 个（无外汇）
FxCashBalance: 0
```

### 结论
外汇持仓在成交后会显示在 `get_positions.py` 中，但可能一段时间后被系统轧差处理。实时查询可以看到当前持仓。

## 飞书 API 集成

### 集成方式
- 使用应用机器人（App ID + App Secret）
- 通过 `tenant_access_token` 发送消息
- 发送到指定群聊（Chat ID）

### 配置信息

| 配置项 | 值 |
|--------|-----|
| App ID | `cli_a9f5b420c9f85cca` |
| App Secret | `dD87XinteNoxupSbKimr9qkfQh6MVdAS` |
| App Token | `t-g10426huWUBYZ6F4YBKKHX7O4EXYZYVQY6INJE7Q` |
| Chat ID | `oc_c662ae6c37140f6daab19c0de30dbfd3` |
| 群名 | 美道微家办 |
| 发送对象 | 飞书机器人（非群聊） |

### API 端点
```
POST https://open.feishu.cn/open-apis/im/v1/messages
Params: receive_id_type=chat_id
Headers: Authorization: Bearer <tenant_access_token>
```

### 配置方法

**方式1: 环境变量（推荐）**

在 `~/.bashrc` 或 `~/.zshrc` 中添加:
```bash
export FEISHU_APP_ID="cli_a9f5b420c9f85cca"
export FEISHU_APP_SECRET="你的App Secret"
export FEISHU_CHAT_ID="oc_c662ae6c37140f6daab19c0de30dbfd3"
```

然后执行: `source ~/.bashrc`

**方式2: 配置文件**

```bash
cp trading/config/.env.example trading/config/.env
# 编辑 .env 填入 App Secret
```

### 测试配置

```bash
# 检查配置状态
python3 trading/config/feishu_config.py

# 发送测试消息
python3 run_at.py 60 "echo '测试'" --feishu
```

### 注意事项
- 飞书文本消息不支持 `\n` 换行，需要使用真实换行符
- 建议使用 `rich` 或 `card` 类型获得更好的显示效果

## Feishu API 错误修复 (2026-02-06)

### 错误信息
```
"field":"receive_id_type","value":"conversation_id"
"receive_id_type is optional, options: [open_id,user_id,union_id,email,chat_id]"
```

### 问题原因
使用 `conversation_id` 类型的 ID（`oc_` 前缀）时，需要指定 `receive_id_type` 为 `chat_id`，而不是 `conversation_id`。

### 解决方案
在 API 请求中添加参数：
```python
params = {"receive_id_type": "chat_id"}
message = {
    "receive_id": FEISHU_CONVERSATION_ID,  # oc_c662ae6c37140f6daab19c0de30dbfd3
    "msg_type": "text",
    "content": json.dumps({"text": "消息内容"}),
}
resp = requests.post(url, params=params, json=message, headers=headers)
```

### 代码修复
- 文件: `webhook_bridge.py`
- 删除重复的 `send_rich_card` 函数
- 统一使用 `receive_id_type: chat_id`

## Webhook 中转服务

### 服务地址
```
http://localhost:5002/webhook
```

### 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/webhook` | POST | 接收 TradingView webhook |
| `/test-api` | POST | 测试 Feishu API |
| `/test-webhook` | POST | 测试 Webhook 方式 |
| `/health` | GET | 健康检查 |

### 启动方式
```bash
cd /Users/wang/.opencode/skills/ibkr/scripts/pair_trading
FEISHU_APP_TOKEN="t-g10426huWUBYZ6F4YBKKHX7O4EXYZYVQY6INJE7Q" \
FEISHU_CONVERSATION_ID="oc_c662ae6c37140f6daab19c0de30dbfd3" \
python webhook_bridge.py 5002
```

### 测试命令
```bash
# 健康检查
curl http://localhost:5002/health

# 测试 API 发送
curl -X POST http://localhost:5002/test-api \
  -H "Content-Type: application/json" \
  -d '{}'

# 模拟 TradingView webhook
curl -X POST http://localhost:5002/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "title": "📈 MNQ-2MYM Long Signal",
    "description": "Spread: $1250\n变化: +$1050",
    "time": "2024-02-06 10:30:00"
  }'
```

## 定时任务实现

### 方案
使用 `run_at.py` 实现定时任务：
- 接受延迟秒数和命令作为参数
- 支持 `--feishu` 标志发送飞书通知
- 后台运行避免超时

### 使用示例
```bash
# 定时任务 + 飞书通知
python3 run_at.py 1800 "python3 place_order.py --symbol GC --close_position --order_type MKT" --feishu

# 实时查询
python3 get_positions.py
python3 get_account_summary.py
```

---
*创建时间: 2026-02-05*
*最后更新: 2026-02-06*
