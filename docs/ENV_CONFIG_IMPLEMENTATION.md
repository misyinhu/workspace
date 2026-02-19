# 环境配置方案实施文档

## 概述

本文档详细说明如何实现 `config/settings.yaml` 环境配置方案，解决本地开发与远程部署的 Python 路径差异问题。

## 实施步骤

### 步骤 1: 配置文件准备 ✅

**已完成**:
- ✅ 扩展 `config/settings.yaml`，添加 environments 配置
- ✅ 创建 `config/env_config.py`，提供配置加载和环境切换功能

**配置内容**:
```yaml
environments:
  local:
    python_path: /usr/local/bin/python3
    project_root: /Users/wang/.opencode/workspace/trading
    use_venv: false
    
  remote:
    python_path: /Users/openclaw/trading_env/bin/python3
    project_root: /Users/openclaw/.openclaw/workspace/trading
    use_venv: true

current: local  # 本地开发时保持 local，远程部署时改为 remote
```

### 步骤 2: 修改脚本文件

#### 2.1 高优先级脚本（必须修改）

**orders/place_order.py** ✅ 已完成

**修改内容**:
```python
# 在文件开头（#!/usr/bin/env python3 之后）添加：
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 确保使用正确的 Python 环境（虚拟环境支持）
try:
    from config.env_config import ensure_venv
    ensure_venv()
except ImportError:
    pass  # 如果 env_config 不存在，继续执行
```

**效果**: 
- 如果使用虚拟环境且当前不是虚拟环境的 Python，会自动切换到正确环境
- 本地开发（use_venv: false）时无影响

#### 2.2 中优先级脚本（建议修改）

**account/get_positions.py**

**修改位置**: 文件开头，import 语句之前

**修改内容**:
```python
#!/usr/bin/env python3
"""查询持仓"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from config.env_config import ensure_venv, get_project_root
    ensure_venv()
except ImportError:
    pass

# 原有 import 语句...
```

**account/get_account_summary.py**

同上模式修改。

#### 2.3 低优先级脚本（可选）

**data/get_historical_data.py**
**orders/get_orders.py**
**orders/cancel_order.py**

这些脚本按需修改，模式同上。

### 步骤 3: 修改 SKILL.md 文档

**位置**: `~/.openclaw/workspace/trading/SKILL.md`

**修改内容**:

1. **在"重要调用语法"部分添加环境说明**:
```markdown
## 环境配置

本项目支持本地开发和远程部署两种环境，通过 `config/settings.yaml` 管理：

- **本地开发** (`current: local`): 使用系统 Python，不激活虚拟环境
- **远程部署** (`current: remote`): 使用虚拟环境 Python (`/Users/openclaw/trading_env/bin/python3`)

脚本会自动检测并切换到正确的 Python 环境。
```

2. **更新调用命令**（可选，因为脚本已自动处理）:

保持原有调用方式不变：
```bash
python3 ~/.openclaw/workspace/trading/orders/place_order.py ...
```

但需要在调用前确保环境变量或配置文件正确。

### 步骤 4: 部署到远程机器

#### 4.1 复制配置文件

```bash
# 在本地执行
scp config/settings.yaml openclaw@100.102.240.31:~/.openclaw/workspace/trading/config/
scp config/env_config.py openclaw@100.102.240.31:~/.openclaw/workspace/trading/config/
scp orders/place_order.py openclaw@100.102.240.31:~/.openclaw/workspace/trading/orders/
```

#### 4.2 修改远程配置

SSH 登录远程机器后：

```bash
# 编辑配置文件
nano ~/.openclaw/workspace/trading/config/settings.yaml

# 修改 current: local 为 current: remote
current: remote
```

#### 4.3 测试验证

```bash
# 测试环境配置
source /Users/openclaw/trading_env/bin/activate
python3 ~/.openclaw/workspace/trading/config/env_config.py

# 预期输出：
# 当前环境: remote
# Python 路径: /Users/openclaw/trading_env/bin/python3
# 使用虚拟环境: True

# 测试下单脚本
python3 ~/.openclaw/workspace/trading/orders/place_order.py --help
# 不应再出现 ModuleNotFoundError: No module named 'ib_insync'
```

### 步骤 5: 更新 webhook 服务

**问题**: webhook_bridge.py 调用 place_order.py 时可能使用系统 Python

**解决方案**: 修改 webhook_bridge.py 的 subprocess 调用

**修改位置**: `notify/webhook_bridge.py`

**修改前**:
```python
subprocess.run([
    "python3", 
    os.path.expanduser("~/.openclaw/workspace/trading/orders/place_order.py"),
    ...
])
```

**修改后**:
```python
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.env_config import get_python_path

subprocess.run([
    get_python_path(),  # 使用配置中的 Python 路径
    os.path.expanduser("~/.openclaw/workspace/trading/orders/place_order.py"),
    ...
])
```

**重启服务**:
```bash
launchctl restart com.openclaw.webhook
```

### 步骤 6: 添加 .gitignore

确保本地配置不提交到 git：

```bash
# 添加到 .gitignore
echo "config/settings.yaml" >> .gitignore

# 创建示例文件
cp config/settings.yaml config/settings.yaml.example
```

## 测试清单

### 本地测试
- [ ] `python3 config/env_config.py` 显示 local 环境
- [ ] `python3 orders/place_order.py --help` 正常执行
- [ ] 不使用虚拟环境（use_venv: false）时无额外输出

### 远程测试
- [ ] SSH 登录后修改 `current: remote`
- [ ] `python3 config/env_config.py` 显示 remote 环境
- [ ] `python3 orders/place_order.py --help` 使用虚拟环境 Python
- [ ] 飞书下单功能正常

## 回滚方案

如需回滚：

```bash
# 恢复备份（如有）
cp orders/place_order.py.bak orders/place_order.py

# 或手动删除添加的代码段（import sys 到 except ImportError 之间）
```

## 预期工作量

| 任务 | 预计时间 | 状态 |
|------|----------|------|
| 配置文件准备 | 10 分钟 | ✅ 已完成 |
| 修改 place_order.py | 5 分钟 | ✅ 已完成 |
| 修改其他脚本（5个） | 15 分钟 | ✅ 已完成 |
| 更新 SKILL.md | 10 分钟 | ✅ 已完成 |
| 部署到远程机器 | 10 分钟 | ⏳ 待执行 |
| 测试验证 | 15 分钟 | ⏳ 待执行 |
| **总计** | **约 65 分钟** | |

## 执行进度

### ✅ 已完成
- [x] 配置文件准备 (`config/settings.yaml`, `config/env_config.py`)
- [x] 修改 `orders/place_order.py`
- [x] 修改 `account/get_positions.py`
- [x] 修改 `account/get_account_summary.py`
- [x] 修改 `data/get_historical_data.py`
- [x] 修改 `orders/get_orders.py`
- [x] 修改 `orders/cancel_order.py`
- [x] 更新 SKILL.md 文档

### ⏳ 待执行
- [ ] 部署到远程机器并测试 |

## 下一步行动

1. **立即执行**: 继续修改其他关键脚本（get_positions.py, get_account_summary.py）
2. **然后执行**: 更新 SKILL.md 文档
3. **最后执行**: 部署到远程机器并测试

**是否继续执行下一步？**
