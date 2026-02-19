# 外汇交易监控系统 - 任务规划

## 项目目标
创建一个价差交易监控系统，支持：
- Z120 M5 价差监控 (HSTECH/MCH.HK)
- 飞书通知集成
- 命令行界面
- 实时监控功能

## 任务清单

### Phase 1: 基础架构 ✅ 已完成
- [x] 安装 IBKR 交易技能
- [x] 安装飞书通知技能
- [x] 安装 planning-with-files 技能
- [x] 配置 IB Gateway 连接
- [x] 配置飞书 API

### Phase 2: 核心功能 ✅ 已完成
- [x] 下单交易功能（外汇、期货、股票）
- [x] 持仓查询功能
- [x] 账户余额查询
- [x] 飞书通知集成
- [x] 定时任务功能

### Phase 3: Z120 M5 监控 ✅ 已完成
- [x] 创建 Z120 M5 监控系统
- [x] 集成飞书通知
- [x] 端到端测试通过

### Phase 4: 待完成
- [ ] 配置实时监控参数
- [ ] 优化飞书消息格式
- [ ] 添加性能指标

### Phase 5: 文档和优化
- [ ] 更新 SKILL.md 文档
- [ ] 优化错误处理
- [ ] 添加单元测试

## 当前状态

### 服务状态
- webhook_bridge.py: 运行中 (端口 5002)
- 飞书通知: ✅ 正常工作

### 文件清单
```
/Users/wang/.opencode/skills/ibkr/scripts/pair_trading/
├── mnq2mym_spread_monitor.pine    # TradingView 指标
└── webhook_bridge.py              # Webhook 中转服务
```

## 下一步行动

1. **配置实时监控**
   - 设置监控参数
   - 优化通知格式

2. **优化飞书消息**
   - 添加交易建议按钮
   - 优化显示样式

## 飞书配置（已验证）

```
App Token: t-g10426huWUBYZ6F4YBKKHX7O4EXYZYVQY6INJE7Q
Chat ID: oc_c662ae6c37140f6daab19c0de30dbfd3
发送对象: 飞书机器人（非群聊）
```

---
*创建时间: 2026-02-05*
*最后更新: 2026-02-19*

## 2026-02-18 会话记录

### 已完成的工作

#### 1. 远程环境部署 webhook 服务 ✅
- **目标机器**: `100.102.240.31` (macOS 10.15, OpenClaw)
- **任务**: 部署 Z120 价差监控 webhook 服务 (端口 5002)
- **执行内容**:
  - 安装 Flask + requests 依赖到虚拟环境
  - 配置 launchd 开机自启 (`~/Library/LaunchAgents/com.openclaw.webhook.plist`)
  - 启动服务并测试验证
- **测试结果**:
  - ✅ Health: `{"status":"ok"}`
  - ✅ Webhook: 飞书消息发送成功
  - ✅ 开机自启: 已配置

#### 2. 修复端口访问问题 ✅
- **问题**: 端口 18789 最初 Connection refused
- **原因**: OpenClaw 服务使用旧版 TLS，新客户端不支持
- **解决方案**: 使用 HTTP 而非 HTTPS 访问
- **状态**: 已解决，HTTP 访问正常

### 待办事项 (TODO)

#### 高优先级
- [x] **实现环境配置方案** (config/settings.yaml)
  - **问题**: 本地开发和远程部署的 Python 路径不同
  - **方案**: 创建 `config/settings.yaml`，包含 local/remote 两套配置
  - **配置内容**:
    ```yaml
    environments:
      local:
        python_path: /usr/bin/python3
        project_root: /Users/yourname/trading
        use_venv: false
      remote:
        python_path: /Users/openclaw/trading_env/bin/python3
        project_root: /Users/openclaw/.openclaw/workspace/trading
        use_venv: true
    current: local  # 默认本地
    ```
  - **实现步骤**:
    1. ✅ 创建 `config/settings.yaml` 文件
    2. ✅ 创建 `config/env_config.py` 配置加载模块
    3. ✅ 修改所有交易脚本使用配置
    4. ✅ 确保 webhook 调用也使用虚拟环境
  - **状态**: ✅ 已完成
  - **修改的文件**:
    - config/settings.yaml
    - config/env_config.py
    - orders/place_order.py
    - orders/get_orders.py
    - orders/cancel_order.py
    - account/get_positions.py
    - account/get_account_summary.py
    - account/get_trades.py
    - account/get_trades_year.py
    - data/get_historical_data.py
    - data/get_realtime_data.py
    - z120_monitor/z120_scheduler.py
    - z120_monitor/core/generic_spread.py
    - SKILL.md (添加环境配置说明)

#### 中优先级
- [ ] **修复 ib_insync 导入问题**
  - **问题**: 下单脚本使用系统 Python，但 ib_insync 只在虚拟环境
  - **临时方案**: 手动指定虚拟环境 Python 路径
  - **长期方案**: 结合 settings.yaml 自动切换

#### 低优先级
- [ ] **部署文档整理**
  - 将本次部署过程整理为部署手册
  - 记录常见问题和解决方案

### 重要信息

#### 远程机器配置
```
机器: 100.102.240.31
用户: openclaw / claw
虚拟环境: /Users/openclaw/trading_env
项目目录: /Users/openclaw/.openclaw/workspace/trading
Webhook: http://100.102.240.31:5002
```

#### 管理命令
```bash
# 重启 webhook 服务
launchctl restart com.openclaw.webhook

# 查看日志
tail -f ~/logs/webhook.log
tail -f ~/logs/webhook.error.log
```

---
*创建时间: 2026-02-05*
*最后更新: 2026-02-06*

---
*创建时间: 2026-02-05*
*最后更新: 2026-02-06*
