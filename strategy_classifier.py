#!/usr/bin/env python3
"""
策略分类模块 - 基于历史交易识别交易策略类型

用于从 IB Gateway 获取交易数据并自动分类策略类型，
作为回测系统的前置模块。

Usage:
    python strategy_classifier.py --days 90
"""

import json
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ib_insync import IB, ExecutionFilter
import nest_asyncio


@dataclass
class Trade:
    """单笔交易"""
    time: datetime
    symbol: str
    sec_type: str
    exchange: str
    action: str  # BOT (买入) / SLD (卖出)
    quantity: float
    price: float
    commission: float
    account: str


@dataclass
class Strategy:
    """策略分类"""
    name: str
    description: str
    trades: List[Trade] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)


class StrategyClassifier:
    """策略分类器"""
    
    # 策略类型定义
    STRATEGY_PATTERNS = {
        "forex_spot": {
            "name": "外汇即期交易",
            "sec_types": ["CASH"],
            "description": "外汇即期货币对交易 (如 AUD/USD, GBP/USD)",
            "indicators": ["IDEALPRO", "FOREX"],
        },
        "futures_intraday": {
            "name": "期货日内交易",
            "sec_types": ["FUT"],
            "description": "期货日内频繁交易，平仓不留隔夜持仓",
            "indicators": ["multiple_entries_same_day", "no_overnight"],
        },
        "futures_swing": {
            "name": "期货波段交易",
            "sec_types": ["FUT"],
            "description": "期货隔夜持仓，追求中短期趋势",
            "indicators": ["overnight_hold"],
        },
        "futures_spread": {
            "name": "期货价差交易",
            "sec_types": ["FUT"],
            "description": "跨期或跨品种价差套利 (如 FU/LU, MNMYM)",
            "indicators": ["spread_pair", "hedge_ratio"],
        },
        "options_iron_condor": {
            "name": "铁鹰策略",
            "sec_types": ["OPT"],
            "description": "期权铁鹰套利",
            "indicators": ["multi_leg", "neutral"],
        },
        "options_covered_call": {
            "name": "备兑看涨",
            "sec_types": ["OPT"],
            "description": "持有标的并卖出看涨期权",
            "indicators": ["stock_hedge"],
        },
    }
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4002):
        self.host = host
        self.port = port
        self.trades: List[Trade] = []
        self.strategies: Dict[str, Strategy] = {}
        
    def connect(self, client_id: int = 99) -> bool:
        """连接 IB Gateway"""
        self.ib = IB()
        try:
            self.ib.connect(self.host, self.port, clientId=client_id, timeout=10)
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
            
    def fetch_trades(self, days: int = 90) -> List[Trade]:
        """获取历史交易"""
        try:
            # 使用异步方式获取更多成交
            import asyncio
            
            async def _fetch():
                await self.ib.connectAsync(self.host, self.port, clientId=99, timeout=10)
                result = await self.ib.reqExecutionsAsync(ExecutionFilter())
                return result
            
            nest_asyncio.apply()
            fills = asyncio.run(_fetch())
            
            # 过滤时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            self.trades = []
            for fill in fills:
                exec_time = fill.execution.time
                # 统一为 naive datetime 进行比较
                if exec_time.tzinfo is not None:
                    exec_time_naive = exec_time.replace(tzinfo=None)
                else:
                    exec_time_naive = exec_time
                    
                start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
                end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
                
                if start_naive <= exec_time_naive <= end_naive:
                    trade = Trade(
                        time=exec_time,
                        symbol=fill.contract.symbol,
                        sec_type=fill.contract.secType,
                        exchange=fill.contract.exchange,
                        action=fill.execution.side,
                        quantity=fill.execution.cumQty,
                        price=fill.execution.price,
                        commission=fill.commissionReport.commission if fill.commissionReport else 0,
                        account=fill.execution.acctNumber,
                    )
                    self.trades.append(trade)
            
            # 按时间排序
            self.trades.sort(key=lambda x: x.time)
            return self.trades
            
        except Exception as e:
            print(f"获取交易失败: {e}")
            return []
            
    def classify_strategies(self) -> Dict[str, Strategy]:
        """分类策略"""
        self.strategies = {}
        
        # 按品种分组
        by_symbol = {}
        for trade in self.trades:
            key = f"{trade.symbol}_{trade.sec_type}"
            if key not in by_symbol:
                by_symbol[key] = []
            by_symbol[key].append(trade)
        
        # 分析每个品种的交易模式
        for symbol_key, trades in by_symbol.items():
            symbol, sec_type = symbol_key.split("_", 1)
            
            # 外汇即期分析
            if sec_type == "CASH":
                strategy_name = "forex_spot"
                if strategy_name not in self.strategies:
                    self.strategies[strategy_name] = Strategy(
                        name="外汇即期交易",
                        description="外汇即期货币对交易"
                    )
                self.strategies[strategy_name].trades.extend(trades)
                
            # 期货分析
            elif sec_type == "FUT":
                self._analyze_futures(trades)
                
        # 计算统计信息
        for strategy in self.strategies.values():
            strategy.stats = self._calculate_stats(strategy.trades)
            
        return self.strategies
    
    def _analyze_futures(self, trades: List[Trade]):
        """分析期货交易模式"""
        if not trades:
            return
            
        # 检查是否日内交易（当天全部平仓）
        dates = set(t.time.date() for t in trades)
        
        # 按日期分析
        for date in dates:
            day_trades = [t for t in trades if t.time.date() == date]
            total_buy = sum(t.quantity for t in day_trades if t.action == "BOT")
            total_sell = sum(t.quantity for t in day_trades if t.action == "SLD")
            
            # 如果买卖基本持平，可能是日内交易
            if abs(total_buy - total_sell) < 0.01:
                strategy_name = "futures_intraday"
                if strategy_name not in self.strategies:
                    self.strategies[strategy_name] = Strategy(
                        name="期货日内交易",
                        description="期货日内交易，不隔夜"
                    )
                self.strategies[strategy_name].trades.extend(day_trades)
            else:
                # 有持仓过夜
                strategy_name = "futures_swing"
                if strategy_name not in self.strategies:
                    self.strategies[strategy_name] = Strategy(
                        name="期货波段交易",
                        description="期货隔夜持仓"
                    )
                self.strategies[strategy_name].trades.extend(day_trades)
                
    def _calculate_stats(self, trades: List[Trade]) -> Dict:
        """计算策略统计"""
        if not trades:
            return {}
            
        total_volume = sum(t.quantity for t in trades)
        total_commission = sum(t.commission for t in trades)
        buy_count = sum(1 for t in trades if t.action == "BOT")
        sell_count = sum(1 for t in trades if t.action == "SLD")
        
        # 交易天数
        trading_dates = len(set(t.time.date() for t in trades))
        
        # 计算盈亏（需要价格变化）
        # 这里简化处理
        
        return {
            "total_trades": len(trades),
            "total_volume": total_volume,
            "total_commission": total_commission,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "trading_days": trading_dates,
            "avg_daily_trades": len(trades) / trading_dates if trading_dates > 0 else 0,
        }
        
    def get_strategy_summary(self) -> Dict:
        """获取策略摘要"""
        summary = {
            "fetch_date": datetime.now().isoformat(),
            "total_trades": len(self.trades),
            "strategies": {}
        }
        
        for name, strategy in self.strategies.items():
            summary["strategies"][name] = {
                "name": strategy.name,
                "description": strategy.description,
                "trade_count": len(strategy.trades),
                "stats": strategy.stats
            }
            
        return summary
        
    def export_for_backtest(self) -> Dict:
        """导出为回测模块格式"""
        return {
            "strategies": [
                {
                    "type": name,
                    "name": s.name,
                    "description": s.description,
                    "trades": [
                        {
                            "date": t.time.strftime("%Y-%m-%d"),
                            "time": t.time.strftime("%H:%M:%S"),
                            "symbol": t.symbol,
                            "action": t.action,
                            "quantity": t.quantity,
                            "price": t.price,
                        }
                        for t in s.trades
                    ],
                    "stats": s.stats
                }
                for name, s in self.strategies.items()
            ]
        }


def main():
    parser = argparse.ArgumentParser(description="策略分类器")
    parser.add_argument("--days", type=int, default=90, help="获取过去N天的数据")
    parser.add_argument("--port", type=int, default=4002, help="IB Gateway 端口")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()
    
    print(f"=== IB Gateway 策略分类器 ===")
    print(f"获取过去 {args.days} 天的数据...")
    
    classifier = StrategyClassifier(port=args.port)
    
    if not classifier.connect():
        print("无法连接 IB Gateway")
        return
        
    trades = classifier.fetch_trades(days=args.days)
    print(f"获取到 {len(trades)} 笔交易")
    
    if not trades:
        print("没有找到交易记录")
        classifier.ib.disconnect()
        return
        
    # 显示交易详情
    print("\n=== 交易明细 ===")
    for t in trades:
        print(f"{t.time.strftime('%Y-%m-%d %H:%M:%S')} | {t.symbol} | {t.sec_type} | {t.action} | {t.quantity} @ {t.price}")
        
    # 分类策略
    strategies = classifier.classify_strategies()
    
    print("\n=== 策略分类结果 ===")
    summary = classifier.get_strategy_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    
    # 导出回测数据
    backtest_data = classifier.export_for_backtest()
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(backtest_data, f, indent=2, ensure_ascii=False)
        print(f"\n已导出到: {args.output}")
        
    classifier.ib.disconnect()


if __name__ == "__main__":
    main()