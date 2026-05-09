# 配置项

## 敏感配置 (.streamlit/secrets.toml)

敏感配置存储在以下位置：

| 项目 | 路径 |
|------|------|
| trading 根目录 | `.streamlit/secrets.toml` |
| kanban | `kanban/.streamlit/secrets.toml` |

```toml
# kanban/.streamlit/secrets.toml 示例
OKX_API_KEY = "your-api-key"
OKX_SECRET_KEY = "your-secret-key"
OKX_PASSPHRASE = "your-passphrase"
TV_WEBHOOK_URL = ""
WEBHOOK_URL = ""
IB_HOST = "127.0.0.1"
IB_PORT = 4001
```

| 变量 | 说明 |
|------|------|
| `OKX_API_KEY` | OKX API 密钥 |
| `OKX_SECRET_KEY` | OKX 密钥 |
| `OKX_PASSPHRASE` | OKX 密码 |
| `WEBHOOK_URL` | 钉钉/飞书 Webhook 地址 |
| `DATA_DIR` | 数据存储目录 (默认: `data/`) |
| `IB_HOST` | Interactive Brokers 主机 |
| `IB_PORT` | Interactive Brokers 端口 |
| `TV_WEBHOOK_URL` | TradingView Webhook 地址 |

## 配置读取

在 `kanban/src/config.py` 中通过 `get_secrets()` 函数读取：

```python
from kanban.src.config import get_okx_api_key, get_okx_secret_key

api_key = get_okx_api_key()
```

## 注意事项

- **secrets.toml 已加入 .gitignore**，不要提交到版本控制
- **API 密钥**: 通过 streamlit secrets 读取，不再硬编码在 yaml
- **storage目录**: `data/` 已加入 `.gitignore`，运行时自动创建
- **Python**: 项目使用 Python 3.13+ 特有语法

## 快捷命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run kanban/app.py

# 代码检查
ruff check .

# 运行测试
pytest tests/
```
