# get_realtime_data.py 使用说明

## 📋 功能说明

`get_realtime_data.py` 是一个通用的实时价格查询工具，支持股票、期货、CFD等多种金融工具的实时价格查询。

## 🎯 基本用法

```bash
# 查询股票
python get_realtime_data.py --symbol AAPL --sec_type STK

# 查询期货
python get_realtime_data.py --symbol MNQ --sec_type FUT --exchange CME --local_symbol MNQH6

# JSON格式输出
python get_realtime_data.py --symbol AAPL --format json
```

## 📊 参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--symbol` | ✅ | - | 品种代码 |
| `--exchange` | ❌ | SMART | 交易所 |
| `--sec_type` | ❌ | STK | 证券类型 (STK/FUT/CFD) |
| `--currency` | ❌ | USD | 货币 |
| `--local_symbol` | ❌ | "" | 本地合约代码 (期货必需) |
| `--timeout` | ❌ | 10 | 超时时间(秒) |
| `--format` | ❌ | json | 输出格式 (json/table) |

## 🔧 证券类型说明

### 股票 (STK)
```bash
python get_realtime_data.py --symbol AAPL --sec_type STK
python get_realtime_data.py --symbol TSLA --sec_type STK --exchange NASDAQ
```

### 期货 (FUT)
```bash
# 需要指定本地合约代码
python get_realtime_data.py --symbol MNQ --sec_type FUT --exchange CME --local_symbol MNQH6
python get_realtime_data.py --symbol GC --sec_type FUT --exchange COMEX --local_symbol GCG6
```

### CFD
```bash
python get_realtime_data.py --symbol EURUSD --sec_type CFD
```

## 📋 常见期货合约代码

### 股指期货
- **MNQ**: 纳斯达克100微型期货 (合约代码: MNQH6, MNQM6, MNQU6)
- **MYM**: 道琼斯微型期货 (合约代码: M6YM, M6YMM, M6YMU)
- **ES**: 标普500期货 (合约代码: ESH6, ESM6, ESU6)

### 商品期货
- **GC**: 黄金期货 (合约代码: GCG6, GCM6, GCU6)
- **MGC**: 微型黄金期货 (合约代码: MGCJ6, MGCM6, MGCN6)

### 合约代码规则
- **月份代码**: F=1月, G=2月, H=3月, J=4月, K=5月, M=6月, N=7月, Q=8月, U=9月, V=10月, X=11月, Z=12月
- **年份代码**: 6=2026, 7=2027
- **示例**: MNQH6 = MNQ 2026年3月合约

## 📊 输出格式

### 表格格式
```
📊 AAPL 实时价格
========================================
品种: AAPL
交易所: SMART
类型: STK
时间: 2026-02-09T08:41:08.873554
最新价: 189.50
买价: 189.48
卖价: 189.52
成交量: 1000000
买量: 100
卖量: 200
```

### JSON格式
```json
{
  "symbol": "AAPL",
  "exchange": "SMART",
  "timestamp": "2026-02-09T08:41:08.873554",
  "bid": 189.48,
  "ask": 189.52,
  "last": 189.50,
  "volume": 1000000,
  "bid_size": 100,
  "ask_size": 200,
  "contract_info": {
    "symbol": "AAPL",
    "sec_type": "STK",
    "exchange": "SMART",
    "currency": "USD"
  }
}
```

## ⚠️ 常见错误和解决方案

### 1. 连接错误
```
❌ 错误: [Errno 61] Connect call failed ('127.0.0.1', 4002)
```
**解决方案**:
- 启动 IBKR Gateway 或 TWS
- 确保端口 4002 开放
- 启用 "Enable ActiveX and Socket Clients"

### 2. 合约错误
```
Error 321: 请输入本地符号或到期日
```
**解决方案**:
- 期货合约需要指定 `--local_symbol`
- 使用正确的合约代码格式

### 3. 市场数据错误
```
Error 10089: 请求的市场数据对于API来说需要额外订阅
```
**解决方案**:
- 检查IBKR账户的市场数据订阅
- 使用可用的市场数据类型
- 尝试在TWS中手动订阅该市场数据

### 4. 无数据错误
```
Error 10197: 您的真实账户记录无市场数据
```
**解决方案**:
- 检查合约是否已到期
- 确认市场开放时间
- 使用正确的交易所

## 🕐 市场时间

### 美股
- **交易时间**: 美东时间 9:30-16:00 (周一至周五)
- **夏令时**: 北京时间 21:30-次日4:00
- **冬令时**: 北京时间 22:30-次日5:00

### 期货
- **交易时间**: 美东时间 17:00-次日16:00 (周日-周五)
- **休市时间**: 美东时间 16:15-17:00

## 🔧 IBKR Gateway 配置

1. **启动 IBKR Gateway**
2. **配置 API**:
   - 勾选 "Enable ActiveX and Socket Clients"
   - 端口设置: 4002 (实盘) 或 4001 (模拟)
   - 不勾选 "Read-only API"
3. **登录账户**
4. **确认权限**: 确保有相应的市场数据订阅

## 💡 使用技巧

1. **查看合约代码**: 在TWS中搜索品种，查看合约详情
2. **市场数据检查**: 先在TWS中确认能看到该品种的实时数据
3. **时间考虑**: 注意各市场的交易时间
4. **合约到期**: 期货合约注意到期时间，及时切换主力合约

## 📞 技术支持

如遇到问题，请检查：
1. IBKR Gateway 运行状态
2. 网络连接
3. 账户权限和订阅
4. 合约代码正确性
5. 市场开放时间