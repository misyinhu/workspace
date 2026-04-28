# IB Symbol 数据获取修复计划

## 问题分析

### 根因
- `kanban/src/data.py` 第 165 行：当 `source="ib"` 时，调用 `get_tv_symbol_for_ib(symbol)` 把 "MNQ" 转换成 "MNQ.cme"
- 但 quant-core 的 `IBSource.get_history()` 期望原始 IB 合约代码（如 "MNQ"），不是 TradingView 格式
- `_is_future("MNQ.cme")` 返回 False（因为格式不对），走了股票逻辑
- 股票逻辑对 "MNQ.cme" 这种无效代码返回空列表

### 数据流对比

**当前（错误）**：
```
settings.yaml: symbol="MNQ", source="ib"
  ↓
data.py: get_tv_symbol_for_ib("MNQ") → "MNQ.cme"
  ↓
GET /api/history?symbol=MNQ.cme&source=ib
  ↓
IBSource.get_history("MNQ.cme")
  ↓ _is_future("MNQ.cme") → False (格式不对)
  ↓ qualifyContracts("MNQ.cme") → 空
  ↓ 返回空数据 ❌
```

**修复后（正确）**：
```
settings.yaml: symbol="MNQ", source="ib"
  ↓
data.py: api_symbol = "MNQ" (不转换)
  ↓
GET /api/history?symbol=MNQ&source=ib
  ↓
IBSource.get_history("MNQ")
  ↓ _is_future("MNQ") → True
  ↓ reqContractDetails(MNQ) → 获取期货详情
  ↓ 返回真实数据 ✅
```

## 修复步骤

### Task 1: 修复 data.py IB symbol 转换逻辑

**文件**: `/Users/wang/.opencode/workspace/trading/kanban/src/data.py`

**修改**: 第 164-165 行

```python
# 修改前
elif source == "ib":
    api_symbol = get_tv_symbol_for_ib(symbol)

# 修改后
elif source == "ib":
    # Don't convert - IB source expects raw IB symbols like "MNQ", not "MNQ.cme"
    api_symbol = symbol
```

**验证**:
- 本地测试: `curl "http://localhost:8005/api/history?symbol=MNQ&source=ib&bar=1D&num=2" -H "X-Client-ID: 10"` 应返回数据

### Task 2: 部署到 CXClaw

**命令**: `./scripts/deploy-to-cxclaw.sh`

### Task 3: 验证远程 IB 数据获取

**测试**:
```bash
# MNQ 期货
curl "http://100.82.238.11:8005/api/history?symbol=MNQ&source=ib&bar=1D&num=2" -H "X-Client-ID: 10"

# AAPL 股票
curl "http://100.82.238.11:8005/api/history?symbol=AAPL&source=ib&bar=1D&num=2" -H "X-Client-ID: 10"
```

**预期**: 都应返回实际数据，不是空列表

### Task 4: 浏览器测试 resonance 页面

**步骤**:
1. 打开 http://localhost:8501/resonance
2. 从下拉框选择 "MNQ - E-mini Nasdaq 100"
3. 验证数据是否正确显示 RSI 和价格

**QA 场景**:
- Happy path: MNQ 显示正确数据
- 对比: 与 IB Gateway 的实际 MNQ 数据对比

## 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `kanban/src/data.py` | IB source 时不转换 symbol |

## 回滚方案

如果修复后 IB 数据仍然失败，回滚方法：

```python
elif source == "ib":
    api_symbol = get_tv_symbol_for_ib(symbol)  # 恢复原样
```

## 注意事项

1. **不修改 quant-core 端** - 只修复 trading 端
2. **IB symbol 格式**: MNQ, AAPL, TSLA 等是 settings.yaml 中定义的原始 symbol
3. **tradingview source**: 不受此修复影响，保持原样