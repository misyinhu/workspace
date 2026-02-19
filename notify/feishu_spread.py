#!/usr/bin/env python3
"""
飞书价差查询处理器
接收飞书消息，查询价差并返回结果
"""

import sys
import os
import json
import yaml
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(__file__))
from feishu import FeishuNotifier


class FeishuSpreadQuery:
    """飞书价差查询处理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.notifier = FeishuNotifier(config_path)
        self._load_pairs_config()

    def _load_pairs_config(self) -> Dict[str, str]:
        """加载交易对配置"""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "z120_monitor", "config", "pairs.yaml"
        )
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                pairs = config.get("pairs", [])
                self.pair_names = {
                    pair["name"]: pair["name"].replace("_", "-")
                    for pair in pairs
                    if pair.get("enabled", False)
                }
                return self.pair_names
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.pair_names = {}
            return {}

    def parse_query(self, message: str) -> Optional[str]:
        """解析用户消息，提取交易对查询"""
        message = message.strip()

        if message in ["价差", "查询价差", "spread"]:
            return "all"

        if message.startswith("查询"):
            pair = message[2:].strip()
            return pair

        if message.upper() in ["MNQ-MYM", "MNQ_MYM"]:
            return "MNQ-MYM"

        if message.upper() in ["HSTECH-MCH", "HSTECH_MCH"]:
            return "HSTECH-MCH"

        if "-" in message or "_" in message:
            return message.replace("_", "-").upper()

        return None

    def get_pair_list(self) -> str:
        """获取可用交易对列表"""
        if not self.pair_names:
            return "暂无可用的交易对"

        pairs = list(self.pair_names.keys())
        return "可查询的交易对: " + ", ".join(pairs)

    def query_pair(self, pair_name: str) -> str:
        """查询单个交易对价差"""
        import subprocess

        pair_key = pair_name.replace("-", "_")
        cmd = [
            sys.executable,
            "-m",
            "z120_monitor.core.generic_spread",
            "--pair",
            pair_key,
            "--format",
            "json",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return f"❌ 查询失败: {result.stderr}"

            data = json.loads(result.stdout)

            if "error" in data:
                return f"❌ {data['error']}"

            return self._format_result(data)

        except subprocess.TimeoutExpired:
            return "❌ 查询超时"
        except json.JSONDecodeError:
            return "❌ 结果解析失败"
        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

    def _format_result(self, data: Dict[str, Any]) -> str:
        """格式化查询结果"""
        pair = data.get("pair", "Unknown")
        mode = data.get("mode", "value")
        timestamp = data.get("timestamp", "")[:19]

        lines = [
            f"📊 {pair} 实时价差报告",
            "=" * 40,
            f"⏰ {timestamp}",
            "",
            "💰 价格信息:",
        ]

        prices = data.get("prices", {})
        for symbol, price in prices.items():
            if price and not (
                isinstance(price, float) and (price != price or price != price)
            ):
                lines.append(f"  • {symbol}: {price:,.2f}")
            else:
                lines.append(f"  • {symbol}: 获取失败")

        spread = data.get("spread", {})
        threshold = data.get("threshold", 0)
        signal = data.get("signal", {})
        calculation = data.get("calculation", {})

        if mode == "value":
            spread_value = spread.get("value", 0)
            lines.extend(
                [
                    "",
                    "📈 价差计算:",
                    f"  {calculation.get('details', '')}",
                    f"  = {spread_value:,.2f}",
                ]
            )
        else:
            spread_ratio = spread.get("ratio", 0)
            lines.extend(
                [
                    "",
                    "📈 价差计算:",
                    f"  {calculation.get('details', '')}",
                    f"  = {spread_ratio:.4f}",
                ]
            )

        lines.extend(
            [
                "",
                "🚦 信号信息:",
                f"  类型: {signal.get('signal_type', 'N/A')}",
                f"  操作: {signal.get('action', 'N/A')}",
                f"  原因: {signal.get('reason', 'N/A')}",
                "",
                f"阈值: {threshold:,.2f}",
            ]
        )

        return "\n".join(lines)

    def query_all_pairs(self) -> str:
        """查询所有启用的交易对"""
        results = []

        for pair_key in self.pair_names.keys():
            try:
                import subprocess

                cmd = [
                    sys.executable,
                    "-m",
                    "z120_monitor.core.generic_spread",
                    "--pair",
                    pair_key,
                    "--format",
                    "json",
                ]

                result = subprocess.run(
                    cmd,
                    cwd=os.path.dirname(__file__),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if "error" not in data:
                        spread = data.get("spread", {})
                        signal = data.get("signal", {})
                        mode = data.get("mode", "value")
                        value = spread.get("value" if mode == "value" else "ratio", 0)
                        results.append(
                            f"• {data['pair']}: {value:,.2f} [{signal.get('signal_type', 'N/A')}]"
                        )
                    else:
                        results.append(f"• {pair_key}: 获取失败")
                else:
                    results.append(f"• {pair_key}: 查询失败")

            except Exception as e:
                results.append(f"• {pair_key}: 错误")

        if not results:
            return "暂无数值"

        return "📊 多头价值价差监控\n\n" + "\n".join(results)

    def handle_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """
        处理飞书消息

        Args:
            message: 用户消息
            chat_id: 聊天 ID

        Returns:
            是否发送成功
        """
        query = self.parse_query(message)

        if query is None:
            response = """❌ 无法识别的命令

可用命令:
• 发送 "价差" 或 "查询价差" - 查询所有交易对
• 发送 "MNQ-MYM" 或 "MNQ_MYM" - 查询 MNQ-MYM
• 发送 "HSTECH-MCH" 或 "HSTECH_MCH" - 查询 HSTECH-MCH

当前支持的交易对: MNQ-MYM, HSTECH-MCH"""
            return self.notifier.send_message(response, chat_id)

        if query == "all":
            response = self.query_all_pairs()
            return self.notifier.send_message(response, chat_id)

        pair_name = query.upper()
        response = self.query_pair(pair_name)
        return self.notifier.send_message(response, chat_id)


def main():
    """测试主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="飞书价差查询测试")
    parser.add_argument("--message", type=str, help="要查询的消息")
    parser.add_argument("--list", action="store_true", help="列出所有交易对")
    args = parser.parse_args()

    handler = FeishuSpreadQuery()

    if args.list:
        print(handler.get_pair_list())
        return

    if args.message:
        result = handler.handle_message(args.message)
        print(f"发送结果: {result}")
    else:
        print("请提供 --message 参数")


if __name__ == "__main__":
    main()
