# 配置项

## 敏感配置 (.streamlit/secrets.toml)

敏感配置存储在以下位置：

| 项目 | 路径 |
|------|------|
| trading 根目录 | `.streamlit/secrets.toml` |
| kanban | `kanban/.streamlit/secrets.toml` |

```toml
# .streamlit/secrets.toml 示例（支持 sim/live 两套密钥）
# live 实盘
OKX_LIVE_API_KEY = "your-live-api-key"
OKX_LIVE_SECRET_KEY = "your-live-secret-key"
OKX_LIVE_PASSPHRASE = "your-live-passphrase"

# sim 模拟盘
OKX_SIM_API_KEY = "your-sim-api-key"
OKX_SIM_SECRET_KEY = "your-sim-secret-key"
OKX_SIM_PASSPHRASE = "your-sim-passphrase"

TV_WEBHOOK_URL = ""
WEBHOOK_URL = ""
IB_HOST = "127.0.0.1"
IB_PORT = 4001
```

| 变量 | 说明 |
|------|------|
| `OKX_LIVE_API_KEY` | OKX 实盘 API 密钥 |
| `OKX_LIVE_SECRET_KEY` | OKX 实盘密钥 |
| `OKX_LIVE_PASSPHRASE` | OKX 实盘密码 |
| `OKX_SIM_API_KEY` | OKX 模拟盘 API 密钥 |
| `OKX_SIM_SECRET_KEY` | OKX 模拟盘密钥 |
| `OKX_SIM_PASSPHRASE` | OKX 模拟盘密码 |
| `WEBHOOK_URL` | 飞书 Webhook 地址 |
| `IB_HOST` | Interactive Brokers 主机 |
| `IB_PORT` | Interactive Brokers 端口 |
| `TV_WEBHOOK_URL` | TradingView Webhook 地址 |

## 配置读取

```python
from kanban.src.config import get_okx_flag, get_okx_api_key, get_okx_secret_key

flag = get_okx_flag()  # 返回 "sim" 或 "live"
api_key = get_okx_api_key()  # 根据 flag 自动选择 live/sim 密钥
```

## OKX 交易模式

在 `config/settings.yaml` 中配置：

```yaml
okx:
  flag: sim  # sim=模拟盘, live=实盘
  pairs:
    - symbol: "DOGE-USDT"
      min_size: 1
    - symbol: "ETH-USDT"
      min_size: 10
```

## 服务器部署

### winclaw (100.99.204.126)

**项目路径**: `C:/projects/trading`

**启动 Webhook**:
```bash
# SSH 登录后进入项目目录
cd C:/projects/trading

# 启动 webhook（后台运行）
start /B cmd /c "python notify\webhook_bridge.py > webhook.log 2>&1"

# 或使用 PowerShell
Start-Process -FilePath python -ArgumentList C:\projects\trading\notify\webhook_bridge.py -WorkingDirectory C:\projects\trading -WindowStyle Hidden
```

**检查状态**:
```bash
# 查看 webhook 是否运行
netstat -ano | findstr 5002

# 查看日志
powershell -Command "Get-Content C:\projects\trading\webhook.log"
```

**重启步骤**:
```bash
# 1. 登录服务器
ssh wang@100.99.204.126

# 2. 拉取最新代码
cd C:/projects/trading
git pull

# 3. 删除旧的 okx.yaml（如果存在）
del config\okx.yaml

# 4. 停止旧进程
taskkill //F //IM python.exe

# 5. 重启 webhook
start /B cmd /c "python notify\webhook_bridge.py > webhook.log 2>&1"
```

**远程执行命令**:
```bash
# 从本地执行远程命令
ssh wang@100.99.204.126 "cd C:/projects/trading && git pull"
ssh wang@100.99.204.126 "taskkill //F //IM python.exe"
ssh wang@100.99.204.126 'start /B cmd /c "python notify\webhook_bridge.py"'
```

## 注意事项

- **secrets.toml 已加入 .gitignore**，不要提交到版本控制
- **API 密钥**: 通过 streamlit secrets 读取，不再硬编码在 yaml
- **okx.yaml 已废弃**: 敏感信息已迁移到 secrets.toml
- **Python**: 项目使用 Python 3.13+ 特有语法

## 快捷命令

```bash
# 安装依赖
pip install -r requirements.txt

# 代码检查
ruff check .

# 运行测试
pytest tests/

# 提交代码（本地）
git add -A
git commit -m "描述"
git push
```

## Webhook 测试

```bash
# 本地测试
curl -X POST http://127.0.0.1:5002/tv-webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "status"}'

# 服务器测试
curl -X POST http://alerts.qiaoge.top/tv-webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "账户"}'
```

支持的命令：`status`、`订单`、`持仓`、`账户`、`买入 DOGE-USDT 1` 等。
