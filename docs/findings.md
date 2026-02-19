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

## 项目历史与里程碑

### Phase 1: 项目启动 (2026-02-05)
**目标**: 建立外汇交易监控系统基础架构

**已完成**:
- ✅ 安装 IBKR 交易技能
- ✅ 安装飞书通知技能
- ✅ 配置 IB Gateway 连接 (端口 4001)
- ✅ 配置飞书 API (App ID: cli_a9f5b420c9f85cca)

**关键决策**:
- 选择 TradingView + Webhook + 飞书的架构
- 使用 Python + ib_insync 作为交易接口

### Phase 2: Z120 M5 监控系统 (2026-02-15)
**目标**: 价差监控和自动通知

**已完成**:
- ✅ 多交易对支持 (MNQ_MYM, HSTECH_MCH, RB_CL)
- ✅ 实时价差计算
- ✅ Z120 指标计算（7天历史数据）
- ✅ 飞书 webhook 集成
- ✅ 每小时定时监控
- ✅ 缓存数据管理（7天自动清理）

**技术栈**:
```
TradingView (指标计算)
  ↓
Webhook Bridge (端口 5002)
  ↓
Z120 Scheduler (价差监控)
  ↓
Feishu (飞书通知)
```

### Phase 3: 基础设施升级 (2026-02-19)
**目标**: 支持长期运行 Agent 工作流

**已完成**:
- ✅ 部署远程环境 (100.102.240.31)
- ✅ 创建 feature_list.json (19 功能跟踪)
- ✅ 创建 AGENTS.md (快速恢复指南)
- ✅ 创建 init.sh (环境初始化)
- ✅ 配置 Git 同步 (misyinhu/trading)
- ✅ launchd 开机自启

**技术债务**:
- ⚠️ ib_insync 环境导入问题 (待修复)
- ⚠️ 集成测试框架 (待完善)

### Phase 3: 基础设施升级 (2026-02-19)
**目标**: 支持长期运行 Agent 工作流

**已完成**:
- ✅ 部署远程环境 (100.102.240.31)
- ✅ 创建 feature_list.json (19 功能跟踪)
- ✅ 创建 AGENTS.md (快速恢复指南，本地)
- ✅ 创建 init.sh (开发环境初始化)
- ✅ 配置 Git 同步 (misyinhu/trading)
- ✅ launchd 开机自启
- ✅ 从 Git 移除 settings.yaml (本地配置保护)
- ✅ 重构部署脚本 (deploy.sh + setup-remote.sh)

**技术债务**:
- ⚠️ ib_insync 环境导入问题 (待修复)
- ⚠️ 集成测试框架 (待完善)

### 重要技术发现

#### 1. IB API 外汇持仓查询
**问题**: 外汇订单成交后，使用 `ib.positions()` 查询不到持仓。

**解决方案**:
- 使用 `ib.portfolio()` 查询
- 查询特定外汇合约
- 检查 `accountSummary()` 中的 `FxCashBalance`

**结论**: 外汇持仓在成交后会显示，但可能一段时间后被系统轧差处理。

#### 2. 飞书 API 集成最佳实践
- 使用 `receive_id_type=chat_id` 而不是 `conversation_id`
- 文本消息不支持 `\n` 换行，需使用真实换行符
- 建议使用 `rich` 或 `card` 类型获得更好的显示效果

#### 3. 多环境配置方案
**挑战**: 本地开发 vs 远程部署的 Python 路径不同

**解决方案**:
```yaml
environments:
  local:
    python_path: /usr/local/bin/python3
    use_venv: false
  remote:
    python_path: /Users/openclaw/trading_env/bin/python3
    use_venv: true
```

**实现**: `config/env_config.py` 提供 `ensure_venv()` 自动切换

#### 4. 端口访问问题
**问题**: OpenClaw 端口 18789 使用旧版 TLS，新客户端不支持

**解决**: 改用 HTTP 访问端口 5002

#### 5. 环境配置实施方案
**完整技术方案**详见 `docs/ENV_CONFIG_IMPLEMENTATION.md`

**核心实现**:
- `config/settings.yaml` - 多环境配置
- `config/env_config.py` - 自动环境切换
- 所有脚本添加 `ensure_venv()` 调用

**关键代码**:
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.env_config import ensure_venv
ensure_venv()  # 自动切换到虚拟环境 Python
```

### 经验教训

1. **Git 同步**: 大文件传输使用 tar + scp 比 git clone 更可靠
2. **环境隔离**: 虚拟环境配置必须在脚本层面处理，不能依赖系统 PATH
3. **日志管理**: launchd 服务需要配置 StandardOutPath/StandardErrorPath
4. **配置分离**: 敏感信息（settings.yaml）不应提交到 Git
5. **部署脚本分离**: 
   - `init.sh` 用于本地开发环境（详细检查、调试）
   - `scripts/deploy.sh` 用于生产部署（简洁、自动重启服务）
   - 两者职责不同，不应混用
6. **Git Hook 管理**:
   - Hook 模板提交到 `scripts/post-merge`
   - 首次部署通过 `setup-remote.sh` 复制到 `.git/hooks/`
   - 后续 `git pull` 自动触发部署

### 部署脚本架构 (2026-02-19)

**文件职责**:

| 文件 | 环境 | 用途 |
|------|------|------|
| `init.sh` | 本地开发 | 详细检查、调试、显示进度 |
| `scripts/deploy.sh` | 生产 | 环境修正 + 服务重启 |
| `scripts/post-merge` | Git Hook | 调用 deploy.sh |
| `scripts/setup-remote.sh` | 首次部署 | 安装 hook + 首次部署 |

**部署流程**:

```
首次部署:
  ssh openclaw@100.102.240.31
  cd ~/.openclaw/workspace/trading
  ./scripts/setup-remote.sh

后续更新:
  git pull  # 自动触发 deploy.sh
```

**关键决策**:
- `config/settings.yaml` 从 Git 移除，保护本地配置
- 每次部署强制重启服务，确保使用最新代码
- post-merge hook 只在远程环境执行（检测 `/Users/openclaw/trading_env`）

---
*创建时间: 2026-02-05*
*最后更新: 2026-02-19*
