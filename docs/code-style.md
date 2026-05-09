# 代码风格

## 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | snake_case | `okx_client.py`, `webhook_bridge.py` |
| 类 | PascalCase | `OKXClient`, `Z120Monitor` |
| 函数 | snake_case | `get_ticker()`, `send_alert()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY`, `WEBHOOK_URL` |
| 变量 | snake_case | `price_data`, `order_id` |

## 导入顺序

1. 标准库
2. 第三方库 (streamlit, requests, pandas)
3. 本项目模块 (相对导入)

```python
# 标准库
import json
import time
from pathlib import Path
from typing import Optional, List, Dict

# 第三方库
import streamlit as st
import requests
import pandas as pd

# 本项目模块
from config import WEBHOOK_URL
from okx_client import OKXClient
```

## 类型注解

- 推荐为函数参数和返回值添加类型注解
- 使用 `typing` 模块: `Optional`, `List`, `Dict` 等

```python
def get_ticker(symbol: str, timeout: int = 30) -> dict:
    ...

def send_alert(message: str, webhook_url: str) -> bool:
    ...
```

## 错误处理

- 使用异常处理时捕获具体异常
- 避免裸 `except:`
- 错误信息应包含上下文

```python
# ✅ 正确
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    raise RuntimeError(f"请求失败: {e}") from e

# ❌ 避免
try:
    ...
except:
    pass
```

## 文档字符串

- 公开函数和类使用 docstring
- 中文注释解释"为什么"而非"是什么"

```python
def get_ticker(symbol: str, timeout: int = 30) -> dict:
    """
    获取交易对实时行情。
    
    调用 OKX API 获取指定交易对的最新价格、成交量等数据。
    """
```

---

## PMO 治理框架参考

代码规范遵循 PMO 治理框架 v2.1：

| 文档 | 位置 |
|------|------|
| DEV 角色手册 | ../../../../pmo/docs/role-dev.md |
| PMO 治理架构 | ../../pmo/openspec/specs/PMO-GOVERNANCE.md |

### 提交前检查清单

DEV 提交代码前必须通过：

```bash
# 1. Lint 检查
ruff check .

# 2. 格式化
ruff format .

# 3. 类型检查
mypy .

# 4. 自动化测试
pytest tests/ -v
```

**任一失败都不准提交**。
