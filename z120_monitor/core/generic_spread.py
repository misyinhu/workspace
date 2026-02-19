#!/usr/bin/env python3
"""
通用价差查询模块
支持任意两对品种的价差计算，支持价值价差和价差比率两种模式
"""

import json
import yaml
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from ib_insync import IB, Stock, Future, CFD, util
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# 确保使用正确的 Python 环境（虚拟环境支持）
try:
    from config.env_config import ensure_venv, get_ib_port
    ensure_venv()
except ImportError:
    pass

from client.ibkr_client import get_client_id


class SpreadEngine:
    """价差计算引擎"""

    def __init__(self, asset1_config: Dict[str, Any], asset2_config: Dict[str, Any]):
        self.asset1 = asset1_config
        self.asset2 = asset2_config

    def calculate_spread_value(self, price1: float, price2: float) -> float:
        """计算价值价差"""
        value1 = price1 * self.asset1.get("multiplier", 1) * self.asset1.get("ratio", 1)
        value2 = price2 * self.asset2.get("multiplier", 1) * self.asset2.get("ratio", 1)
        return value1 - value2

    def calculate_spread_ratio(self, price1: float, price2: float) -> float:
        """计算价差比率"""
        value1 = price1 * self.asset1.get("multiplier", 1) * self.asset1.get("ratio", 1)
        value2 = price2 * self.asset2.get("multiplier", 1) * self.asset2.get("ratio", 1)
        if value2 == 0:
            return 0.0
        return value1 / value2


class SignalGenerator:
    """信号生成器"""

    def __init__(self, threshold: float = 1000):
        self.threshold = threshold

    def generate_signal(
        self, mode: str, spread_value: float, spread_ratio: float
    ) -> Dict[str, Any]:
        """生成交易信号"""
        if mode == "value":
            spread = spread_value
        else:
            spread = spread_ratio

        if abs(spread) > self.threshold:
            if spread > 0:
                return {
                    "signal_type": "LONG",
                    "action": "LONG_ASSET1_SHORT_ASSET2",
                    "reason": f"价差 {spread:.2f} 超过阈值 {self.threshold}",
                }
            else:
                return {
                    "signal_type": "SHORT",
                    "action": "SHORT_ASSET1_LONG_ASSET2",
                    "reason": f"价差 {spread:.2f} 低于阈值 -{self.threshold}",
                }
        else:
            return {
                "signal_type": "NO_SIGNAL",
                "action": "HOLD",
                "reason": f"价差 {spread:.2f} 未达到阈值 {self.threshold}",
            }


class ContractBuilder:
    """合约构建器"""

    @staticmethod
    def build(config: Dict[str, Any]):
        """根据配置创建合约对象"""
        sec_type = config.get("sec_type", "STK")
        symbol = config.get("symbol", "")
        exchange = config.get("exchange", "SMART")
        currency = config.get("currency", "USD")
        local_symbol = config.get("local_symbol", "")

        if sec_type == "FUT":
            if local_symbol:
                return Future(
                    symbol=symbol,
                    localSymbol=local_symbol,
                    exchange=exchange,
                    currency=currency,
                )
            else:
                return Future(symbol=symbol, exchange=exchange, currency=currency)
        elif sec_type == "CFD":
            return CFD(symbol=symbol, exchange=exchange, currency=currency)
        else:
            return Stock(symbol=symbol, exchange=exchange, currency=currency)


class DataSource:
    """数据源"""

    def __init__(self, port: int = None):
        if port is None:
            try:
                from config.env_config import get_ib_port
                port = get_ib_port()
            except Exception:
                port = 4001
        self.port = port
        self.ib = None
        self.client_id = None

    def connect(self) -> bool:
        """连接到IBKR"""
        try:
            self.client_id = get_client_id()
            self.ib = IB()
            self.ib.connect("127.0.0.1", self.port, clientId=self.client_id)
            return True
        except Exception as e:
            print(f"连接错误: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()

    def get_price(
        self, config: Dict[str, Any], timeout: int = 15
    ) -> Tuple[Optional[float], Optional[str]]:
        """获取单个资产价格"""
        try:
            contract = ContractBuilder.build(config)
            ticker = self.ib.reqMktData(contract, "", False, False)

            start_time = time.time()
            while time.time() - start_time < timeout:
                util.sleep(0.5)
                if ticker.last > 0 and ticker.bid > 0 and ticker.ask > 0:
                    break

            if ticker.last == 0:
                return None, "市场数据订阅不足或市场休市"

            return ticker.last, None

        except Exception as e:
            return None, str(e)

    def get_prices(
        self,
        asset1_config: Dict[str, Any],
        asset2_config: Dict[str, Any],
        timeout: int = 15,
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """获取两个资产价格"""
        price1, error1 = self.get_price(asset1_config, timeout)
        if error1:
            return None, None, f"资产1获取失败: {error1}"

        price2, error2 = self.get_price(asset2_config, timeout)
        if error2:
            return None, None, f"资产2获取失败: {error2}"

        return price1, price2, None


class GenericSpreadMonitor:
    """通用价差监控器"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "pairs.yaml"
            )
        self.config_path = config_path
        self.pairs = self.load_config()
        self.data_source = DataSource()

    def load_config(self) -> List[Dict[str, Any]]:
        """加载配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("pairs", [])
        except Exception as e:
            print(f"加载配置失败: {e}")
            return []

    def get_pair_config(self, pair_name: str) -> Optional[Dict[str, Any]]:
        """获取交易对配置"""
        for pair in self.pairs:
            if pair.get("name") == pair_name and pair.get("enabled", False):
                return pair
        return None

    def analyze_pair(self, pair_name: str, timeout: int = 15) -> Dict[str, Any]:
        """分析指定交易对"""
        pair_config = self.get_pair_config(pair_name)
        if not pair_config:
            return {
                "error": f"交易对 {pair_name} 未找到或未启用",
                "pair": pair_name,
            }

        mode = pair_config.get("mode", "value")
        threshold = pair_config.get("threshold", 1000)
        assets = pair_config.get("assets", [])

        if len(assets) < 2:
            return {
                "error": f"交易对 {pair_name} 配置错误，资产不足",
                "pair": pair_name,
            }

        asset1_config = assets[0]
        asset2_config = assets[1]

        if not self.data_source.connect():
            return {
                "error": "连接IBKR失败",
                "pair": pair_name,
            }

        try:
            price1, price2, error = self.data_source.get_prices(
                asset1_config, asset2_config, timeout
            )

            if error:
                return {
                    "error": error,
                    "pair": pair_name,
                    "asset1_config": asset1_config,
                    "asset2_config": asset2_config,
                }

            spread_engine = SpreadEngine(asset1_config, asset2_config)
            signal_gen = SignalGenerator(threshold)

            spread_value = spread_engine.calculate_spread_value(price1, price2)
            spread_ratio = spread_engine.calculate_spread_ratio(price1, price2)
            signal = signal_gen.generate_signal(mode, spread_value, spread_ratio)

            result = {
                "pair": pair_name,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "prices": {
                    asset1_config["symbol"]: price1,
                    asset2_config["symbol"]: price2,
                },
                "spread": {
                    "value": spread_value,
                    "ratio": spread_ratio,
                },
                "threshold": threshold,
                "signal": signal,
                "calculation": {
                    "formula": f"spread_{mode}(price1, price2)",
                    "details": f"{asset1_config['symbol']} × {asset1_config.get('multiplier', 1)} × {asset1_config.get('ratio', 1)} "
                    f"{'-' if mode == 'value' else '/'} "
                    f"{asset2_config['symbol']} × {asset2_config.get('multiplier', 1)} × {asset2_config.get('ratio', 1)}",
                },
            }

            return result

        finally:
            self.data_source.disconnect()

    def render_text_report(self, result: Dict[str, Any]) -> str:
        """渲染文本报告"""
        if "error" in result:
            return f"错误: {result['error']}"

        lines = [
            f"📊 {result['pair']} 实时价差报告",
            "=" * 50,
            f"模式: {result['mode']}",
            f"时间: {result['timestamp']}",
            "",
            "价格信息:",
        ]

        for symbol, price in result["prices"].items():
            lines.append(f"  - {symbol}: {price:,.2f}")

        lines.extend(
            [
                "",
                "价差计算:",
                f"  {result['calculation']['details']}",
                f"  = {result['spread']['value']:,.2f}"
                if result["mode"] == "value"
                else f"  = {result['spread']['ratio']:.4f}",
                "",
                "信号信息:",
                f"  类型: {result['signal']['signal_type']}",
                f"  操作: {result['signal']['action']}",
                f"  原因: {result['signal']['reason']}",
                "",
                f"阈值: {result['threshold']}",
            ]
        )

        return "\n".join(lines)

    def list_pairs(self) -> List[str]:
        """列出所有启用的交易对"""
        return [pair["name"] for pair in self.pairs if pair.get("enabled", False)]


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="通用价差查询")
    parser.add_argument("--pair", help="交易对名称，如 MNQ_MYM")
    parser.add_argument("--list", action="store_true", help="列出所有交易对")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="输出格式"
    )
    parser.add_argument("--timeout", type=int, default=15, help="超时时间")
    args = parser.parse_args()

    monitor = GenericSpreadMonitor()

    if args.list:
        pairs = monitor.list_pairs()
        print("📋 可用交易对:")
        for pair in pairs:
            print(f"  - {pair}")
        return

    if not args.pair:
        parser.error("--pair 参数 required")

    result = monitor.analyze_pair(args.pair, args.timeout)

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(monitor.render_text_report(result))


if __name__ == "__main__":
    main()
