#!/usr/bin/env python3
"""
Z120 监控调度器
按照配置定时运行，基于历史价差数据计算 Z120，发出信号时推送飞书通知
"""

import sys
import os
import time
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".."))

# 确保使用正确的 Python 环境（虚拟环境支持）
try:
    from config.env_config import ensure_venv
    ensure_venv()
except ImportError:
    pass

from ib_insync import IB, Stock, Future
import yaml

Z120_PID_FILE = "/tmp/z120_monitor.pid"

try:
    from z120_cache import save_status, get_spread_change, get_cached_spread_history

    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    get_spread_change = None
    get_cached_spread_history = None


def select_main_contract_for_monitoring(contracts, symbol):
    """为监控选择主力合约（季月优先，跳过30天内到期，选择最近的）"""
    from datetime import datetime
    
    now = datetime.now()
    current_day = now.year * 10000 + now.month * 100 + now.day
    quarter_months = [3, 6, 9, 12]
    
    candidates = []
    for d in contracts:
        c = d.contract
        expiry_str = c.lastTradeDateOrContractMonth
        if expiry_str:
            try:
                expiry = int(expiry_str)
                # 跳过30天内到期的合约
                if expiry < current_day + 30:
                    continue
                
                month = expiry % 100
                priority = 0
                if month in quarter_months:
                    priority = 3
                elif month == (now.month % 100) + 1:
                    priority = 2
                else:
                    priority = 1
                    
                candidates.append((priority, expiry, c))
            except:
                continue
    
    if candidates:
        # 按优先级降序，到期日升序（优先选择最近的季月）
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][2]
    
    # 如果没有合适的，返回第一个
    return contracts[0].contract if contracts else None


def get_latest_spreads(pairs_config: Dict) -> Dict[str, float]:
    """一次 IB 连接获取所有交易对的当前价差"""
    try:
        from client.ibkr_client import get_client_id, IBKR_HOST, IBKR_PORT
        import asyncio
        import nest_asyncio

        nest_asyncio.apply()

        async def fetch():
            ib = IB()
            await ib.connectAsync(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

            results = {}
            for pair_name, pair_config in pairs_config.items():
                assets = pair_config.get("assets", [])
                if len(assets) < 2:
                    continue

                try:
                    # 获取资产1
                    a1 = assets[0]
                    c1 = None

                    if a1.get("sec_type") == "FUT":
                        # 自动获取主力合约
                        symbol = a1.get("symbol", "")
                        exchange = a1.get("exchange", "")
                        currency = a1.get("currency", "USD")
                        
                        # 先查询合约列表
                        contracts = ib.reqContractDetails(Future(symbol=symbol, exchange=exchange, currency=currency))
                        if contracts:
                            # 选择主力合约（季月优先）
                            main_contract = select_main_contract_for_monitoring(contracts, symbol)
                            c1 = main_contract
                            print(f"    {symbol} 使用主力合约: {c1.localSymbol}")
                    
                    if not c1:
                        c1 = Stock(
                            symbol=a1.get("symbol", ""),
                            exchange=a1.get("exchange", ""),
                            currency=a1.get("currency", ""),
                        )
                    
                    bars1 = ib.reqHistoricalData(
                        c1,
                        endDateTime="",
                        durationStr="1 D",
                        barSizeSetting="5 mins",
                        whatToShow="TRADES",
                        useRTH=False,
                        formatDate=1,
                    )

                    # 获取资产2
                    a2 = assets[1]
                    c2 = None
                    
                    if a2.get("sec_type") == "FUT":
                        # 自动获取主力合约
                        symbol = a2.get("symbol", "")
                        exchange = a2.get("exchange", "")
                        currency = a2.get("currency", "USD")
                        
                        contracts = ib.reqContractDetails(Future(symbol=symbol, exchange=exchange, currency=currency))
                        if contracts:
                            main_contract = select_main_contract_for_monitoring(contracts, symbol)
                            c2 = main_contract
                            print(f"    {symbol} 使用主力合约: {c2.localSymbol}")
                    
                    if not c2:
                        c2 = Stock(
                            symbol=a2.get("symbol", ""),
                            exchange=a2.get("exchange", ""),
                            currency=a2.get("currency", ""),
                        )
                    
                    bars2 = ib.reqHistoricalData(
                        c2,
                        endDateTime="",
                        durationStr="1 D",
                        barSizeSetting="5 mins",
                        whatToShow="TRADES",
                        useRTH=False,
                        formatDate=1,
                    )

                    if bars1 and bars2:
                        close1 = bars1[0].close
                        close2 = bars2[0].close
                        mult1 = a1.get("multiplier", 1) * a1.get("ratio", 1)
                        mult2 = a2.get("multiplier", 1) * a2.get("ratio", 1)
                        spread = close1 * mult1 - close2 * mult2
                        results[pair_name] = spread
                        print(
                            f"    {pair_name}: {close1:.2f}*{mult1} - {close2:.2f}*{mult2} = {spread:.2f}"
                        )
                except Exception as e:
                    print(f"    ❌ {pair_name} 获取失败: {e}")

            ib.disconnect()
            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(fetch())
        loop.close()
        return results

    except Exception as e:
        print(f"  ❌ 获取价差失败: {e}")
        return {}


def rebuild_history_if_needed(pairs_config: Dict) -> bool:
    """检查历史数据完整性，不足100条则自动获取48天历史数据重建"""
    from z120_cache import get_cached_status, save_status
    from client.ibkr_client import get_client_id, IBKR_HOST, IBKR_PORT
    import asyncio
    import nest_asyncio
    from ib_insync import IB, Stock, Future
    import numpy as np

    print(f"\n🔍 检查历史数据完整性...")

    needs_rebuild = []
    for pair_name, pair_config in pairs_config.items():
        cached = get_cached_status(pair_name)
        history = cached.get("history", []) if cached else []

        if len(history) >= 100:
            print(f"  ✅ {pair_name}: 已有 {len(history)} 条历史数据")
        else:
            print(
                f"  ⚠️ {pair_name}: 只有 {len(history)} 条历史数据（需要 {100 - len(history)} 条）"
            )
            needs_rebuild.append((pair_name, pair_config))

    if not needs_rebuild:
        print(f"  ✅ 所有交易对历史数据完整")
        return False

    print(f"\n📥 开始获取7天历史数据（{len(needs_rebuild)}个交易对）...")

    nest_asyncio.apply()

    async def fetch_7d_history(pair_name, pair_config):
        """获取单个交易对48天历史数据并计算价差"""
        assets = pair_config.get("assets", [])
        if len(assets) < 2:
            print(f"  ❌ {pair_name}: 资产配置不足")
            return 0

        try:
            ib = IB()
            await ib.connectAsync(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

            # 获取资产1的48天历史数据
            a1 = assets[0]
            if a1.get("sec_type") == "FUT" and a1.get("local_symbol"):
                c1 = Future(
                    symbol=a1.get("symbol", ""),
                    localSymbol=a1.get("local_symbol", ""),
                    exchange=a1.get("exchange", ""),
                    currency=a1.get("currency", ""),
                )
            else:
                c1 = Stock(
                    symbol=a1.get("symbol", ""),
                    exchange=a1.get("exchange", ""),
                    currency=a1.get("currency", ""),
                )

            bars1 = ib.reqHistoricalData(
                c1,
                endDateTime="",
                durationStr="7 D",
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
            )

            # 获取资产2的48天历史数据
            a2 = assets[1]
            if a2.get("sec_type") == "FUT" and a2.get("local_symbol"):
                c2 = Future(
                    symbol=a2.get("symbol", ""),
                    localSymbol=a2.get("local_symbol", ""),
                    exchange=a2.get("exchange", ""),
                    currency=a2.get("currency", ""),
                )
            else:
                c2 = Stock(
                    symbol=a2.get("symbol", ""),
                    exchange=a2.get("exchange", ""),
                    currency=a2.get("currency", ""),
                )

            bars2 = ib.reqHistoricalData(
                c2,
                endDateTime="",
                durationStr="7 D",
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
            )

            ib.disconnect()

            if not bars1 or not bars2:
                print(f"  ❌ {pair_name}: 无法获取历史数据")
                return 0

            # 按时间戳匹配计算价差
            mult1 = a1.get("multiplier", 1) * a1.get("ratio", 1)
            mult2 = a2.get("multiplier", 1) * a2.get("ratio", 1)

            # 创建时间戳到价格的映射
            def get_timestamp(bar_date):
                """统一处理日期类型，处理带时区的时间"""
                if hasattr(bar_date, "timestamp"):
                    # 如果带时区，转换为UTC时间戳
                    ts = bar_date.timestamp()
                    return ts
                else:
                    # 如果是date对象，转换为datetime
                    from datetime import datetime as dt

                    return dt.combine(bar_date, dt.min.time()).timestamp()

            price_map1 = {get_timestamp(bar.date): bar.close for bar in bars1}
            price_map2 = {get_timestamp(bar.date): bar.close for bar in bars2}

            # 找到共同的时间戳（只保留最近的7天）
            now_ts = datetime.now().timestamp()
            cutoff_ts = now_ts - 7 * 24 * 3600
            common_timestamps = sorted(
                ts
                for ts in set(price_map1.keys()) & set(price_map2.keys())
                if ts >= cutoff_ts
            )

            if len(common_timestamps) < 100:
                print(
                    f"  ⚠️ {pair_name}: 只有{len(common_timestamps)}个数据点（需要100个）"
                )

            # 计算价差并保存
            count = 0
            for ts in common_timestamps:
                spread = price_map1[ts] * mult1 - price_map2[ts] * mult2
                dt = datetime.fromtimestamp(ts)
                save_status(
                    pair_name=pair_name,
                    zscore=None,
                    spread=spread,
                    mean=0,
                    std=0,
                    threshold=pair_config.get("threshold", 0),
                    timestamp=dt,
                )
                count += 1

            print(f"  ✅ {pair_name}: 已保存 {count} 条历史价差数据")
            return count

        except Exception as e:
            print(f"  ❌ {pair_name}: 获取历史数据失败 - {e}")
            return 0

    # 串行获取每个交易对的历史数据（避免IBKR连接冲突）
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    total_added = 0
    for pair_name, pair_config in needs_rebuild:
        count = loop.run_until_complete(fetch_7d_history(pair_name, pair_config))
        total_added += count
        time.sleep(1)  # 避免请求过快

    loop.close()

    print(f"\n✅ 历史数据重建完成（2天），共 {total_added} 条记录")
    return total_added > 0


class Z120ScheduledMonitor:
    """Z120 定时监控器"""

    def __init__(self):
        self.config_path = str(BASE_DIR / "config" / "config.yaml")
        self.pairs_config_path = str(BASE_DIR / "config" / "pairs.yaml")
        self.settings_path = str(BASE_DIR / ".." / "config" / "settings.yaml")

        self.config = self._load_config()
        self.pairs_config = self._load_pairs_config()
        self.settings = self._load_settings()

        interval_minutes = self.config.get("monitoring", {}).get("interval_minutes", 60)
        self.interval_seconds = interval_minutes * 60
        self.query_only = self.settings.get("query_only", True)

        self.running = False
        self._thread: Optional[threading.Thread] = None

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            return {}

    def _load_settings(self) -> Dict[str, Any]:
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            return {}

    def _load_pairs_config(self) -> Dict[str, Any]:
        try:
            with open(self.pairs_config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return {
                    p["name"]: p
                    for p in data.get("pairs", [])
                    if p.get("enabled", False)
                }
        except Exception as e:
            print(f"❌ 加载交易对配置失败: {e}")
            return {}

    def calculate_zscore(self, spread_values: List[float]) -> Dict[str, Any]:
        """计算 Z120（不管有多少条都用上）"""
        import numpy as np

        if len(spread_values) < 2:
            return {
                "zscore": None,
                "mean": None,
                "std": None,
                "status": "WARMUP",
                "message": f"数据不足 ({len(spread_values)} 条)",
            }

        spreads = np.array(spread_values)
        mean = np.mean(spreads)
        std = np.std(spreads)

        if std == 0 or np.isnan(std):
            return {
                "zscore": None,
                "mean": float(mean),
                "std": float(std),
                "status": "INVALID",
                "message": "标准差为0",
            }

        last_spread = spread_values[0]
        zscore = (last_spread - mean) / std

        return {
            "zscore": float(zscore),
            "mean": float(mean),
            "std": float(std),
            "spread": last_spread,
            "status": "ACTIVE",
            "message": "OK",
        }

    def get_signal(
        self, zscore: Optional[float], oversold: float, overbought: float
    ) -> Dict[str, Any]:
        """生成信号"""
        if zscore is None:
            return {"signal": "WAIT", "action": "HOLD", "reason": "数据不足"}

        if zscore <= oversold:
            return {
                "signal": "OVERSOLD",
                "action": "LONG_SPREAD",
                "reason": f"Z120={zscore:.2f} <= {oversold}",
            }
        elif zscore >= overbought:
            return {
                "signal": "OVERBOUGHT",
                "action": "SHORT_SPREAD",
                "reason": f"Z120={zscore:.2f} >= {overbought}",
            }
        else:
            return {
                "signal": "NEUTRAL",
                "action": "HOLD",
                "reason": f"Z120={zscore:.2f} 在阈值范围内 ({oversold} ~ {overbought})",
            }

    def _run_once(self):
        """执行一次监控"""
        print(f"\n{'=' * 60}")
        print(f"🕐 Z120 监控运行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")

        # 先检查历史数据完整性，不足100条则重建
        rebuild_history_if_needed(self.pairs_config)

        latest_spreads = get_latest_spreads(self.pairs_config)
        print(f"\n✅ 获取到 {len(latest_spreads)} 个交易对的当前价差")

        for pair_name, pair_config in self.pairs_config.items():
            print(f"\n📊 检查交易对: {pair_name}")

            current_spread = latest_spreads.get(pair_name)
            if current_spread is None:
                print(f"  ❌ 无法获取当前价差")
                continue

            pair_threshold = pair_config.get("threshold", 0)
            oversold = pair_config.get("oversold", 0.0)
            overbought = pair_config.get("overbought", 0.0)

            # 从缓存读取历史价差（按7天时间范围筛选）
            spread_history = None
            zresult = None
            zscore = None

            if CACHE_ENABLED and get_cached_spread_history:
                spread_history = get_cached_spread_history(pair_name, days=7)
                if spread_history and len(spread_history) >= 10:
                    zresult = self.calculate_zscore(spread_history)
                    zscore = zresult.get("zscore")

            if zscore is not None:
                print(f"  ✅ 当前价差: {current_spread:.2f}")
                print(f"  ✅ 历史数据: {len(spread_history)} 条")
                print(f"  📈 Z120: {zscore:.2f}")
            else:
                print(f"  ⚠️ 无法计算 Z120（历史数据不足）")

            if pair_threshold > 0:
                print(f"  🎯 价差阈值: {pair_threshold}")
            print(f"  📉 Oversold: {oversold}")
            print(f"  📈 Overbought: {overbought}")

            signal = self.get_signal(zscore, oversold, overbought)
            print(f"  🚦 Signal: {signal['signal']}")

            # 只有当获取到实时价差时才保存（避免重复保存相同值）
            if CACHE_ENABLED and current_spread is not None:
                from z120_cache import get_cached_status

                cached = get_cached_status(pair_name)
                last_spread = cached.get("spread") if cached else None

                # 只有新值与上次不同时才保存
                if last_spread is None or abs(current_spread - last_spread) > 0.01:
                    save_status(
                        pair_name=pair_name,
                        zscore=zscore,
                        spread=current_spread,
                        mean=zresult.get("mean", 0) if zresult else 0,
                        std=zresult.get("std", 0) if zresult else 0,
                        threshold=pair_threshold,
                        oversold=oversold,
                        overbought=overbought,
                    )
                    print(f"  💾 缓存已更新 ({current_spread:.2f})")
                else:
                    print(f"  💾 价差无变化，跳过保存")

            # 检查7天价差变化
            spread_alert = False
            if pair_threshold > 0 and CACHE_ENABLED and get_spread_change:
                change_info = get_spread_change(pair_name, days=7)
                change = change_info.get("change", 0)
                if abs(change) > pair_threshold:
                    direction = "↗️" if change > 0 else "↘️"
                    print(
                        f"  🚨 7天价差变化{direction}: {change:.0f} (阈值: ±{pair_threshold})"
                    )
                    spread_alert = True

            # 发送飞书通知
            if (
                signal["signal"] in ["OVERSOLD", "OVERBOUGHT"] or spread_alert
            ) and zscore is not None:
                print(f"🚨 检测到信号!")
                self._send_feishu(
                    pair_name,
                    zresult,
                    signal,
                    current_spread,
                    pair_threshold,
                    change_info if spread_alert else {},
                )
                self._execute_trade(pair_name, signal, pair_config.get("assets", []))

            time.sleep(0.5)

    def _send_feishu(
        self,
        pair_name: str,
        zresult: Dict,
        signal: Dict,
        current_spread: float,
        pair_threshold: float,
        spread_change_info: Dict,
    ):
        """发送飞书通知"""
        try:
            from notify.feishu import FeishuNotifier

            notifier = FeishuNotifier()

            emoji = "📈" if signal["signal"] == "OVERSOLD" else "📉"
            mode_text = "🔒 仅查询模式" if self.query_only else "✅ 交易模式"

            spread_trigger = ""
            if spread_change_info:
                change = spread_change_info.get("change", 0)
                days = spread_change_info.get("days", 7)
                if abs(change) > pair_threshold:
                    direction = "↗️" if change > 0 else "↘️"
                    spread_trigger = f"\n⚠️ {days}天价差变化{direction}: {change:.0f} (阈值: ±{pair_threshold})"

            message = f"""{emoji} Z120 信号通知

交易对: {pair_name}
信号类型: {signal["signal"]}
Z120 值: {zresult.get("zscore", 0):.2f}
当前价差: {current_spread:.2f}
建议操作: {signal["action"]}
模式: {mode_text}{spread_trigger}

时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

            notifier.send_message(message)
            print(f"  ✅ 飞书通知已发送")
        except Exception as e:
            print(f"  ❌ 飞书通知失败: {e}")

    def _execute_trade(self, pair_name: str, signal: Dict, assets: List[Dict]):
        """执行交易"""
        if self.query_only:
            print(f"  🔒 仅查询模式，跳过交易")
            return
        print(f"  ⚠️ 交易功能待实现")

    def start(self):
        """启动定时监控"""
        if self.running:
            print("监控已在运行中")
            return

        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("✅ Z120 监控已启动")

    def _run_loop(self):
        """定时运行"""
        while self.running:
            try:
                self._run_once()
            except Exception as e:
                print(f"❌ 监控异常: {e}")
            time.sleep(self.interval_seconds)

    def stop(self):
        """停止监控"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("🛑 Z120 监控已停止")


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Z120 监控")
    parser.add_argument("--once", action="store_true", help="只运行一次")
    args = parser.parse_args()

    monitor = Z120ScheduledMonitor()

    if args.once:
        monitor._run_once()
    else:
        monitor.start()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            monitor.stop()


if __name__ == "__main__":
    main()
