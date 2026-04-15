# DOGE/ETH 网格交易机器人部署计划

## 目标
将代码整理到 okx_client 目录，添加实际下单功能，部署到服务器运行

## 当前状态
- 已有: doge_eth_grid_bot.py (仅打印信号，无实际下单)
- 已有: okx_client/okx_client.py (OKX API 封装)
- 已有: config/okx.yaml (API 配置)

## 阶段

### Phase 1: 文件整理
- [ ] 移动 doge_eth_grid_bot.py -> okx_client/grid_bot.py
- [ ] 移动/合并配置到 okx_client/config.yaml

### Phase 2: 添加下单功能
- [ ] 修改 grid_bot.py，集成 OKX 实际下单
- [ ] 添加仓位管理（开仓/平仓/换仓）
- [ ] 添加错误处理和重试

### Phase 3: 服务器部署
- [ ] 打包代码和配置
- [ ] 部署到服务器 100.102.240.31
- [ ] 配置系统服务自动运行

### Phase 4: 测试验证
- [ ] 模拟盘测试
- [ ] 监控运行状态

## 关键决策
- 使用模拟盘 (flag="1") 进行测试
- 保留实盘密钥配置

## 文件清单
- okx_client/
  - __init__.py
  - okx_client.py
  - grid_bot.py (新/移动)
  - config.yaml (新/移动)
