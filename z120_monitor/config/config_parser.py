"""
JSON 配置文件解析器
支持用户自定义品种配置和策略参数
"""

import json
import os
from typing import Dict, Any, Optional


class ConfigParser:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = {}

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(script_dir, "config", "instruments.json")

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            print(f"✅ 配置文件加载成功: {self.config_path}")
            return self.config
        except FileNotFoundError:
            print(f"⚠️ 配置文件未找到: {self.config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件格式错误: {e}")
            return {}

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "instruments": {
                "MNQ": {
                    "symbol": "MNQ",
                    "exchange": "CME",
                    "currency": "USD",
                    "multiplier": 2.0,
                    "ratio": 1,
                },
                "MYM": {
                    "symbol": "MYM",
                    "exchange": "CME",
                    "currency": "USD",
                    "multiplier": 0.5,
                    "ratio": 2,
                },
            },
            "strategy": {
                "threshold": 1000,
                "lookback_days": 7,
                "monitoring_interval": 5,
            },
        }

    def get_instrument_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取指定品种配置"""
        instruments = self.config.get("instruments", {})
        return instruments.get(symbol.upper())

    def get_strategy_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return self.config.get("strategy", {})

    def get_all_instruments(self) -> Dict[str, Dict[str, Any]]:
        """获取所有品种配置"""
        return self.config.get("instruments", {})

    def validate_config(self) -> bool:
        """验证配置文件格式"""
        required_sections = ["instruments", "strategy"]
        for section in required_sections:
            if section not in self.config:
                print(f"❌ 配置缺少必要部分: {section}")
                return False

        instruments = self.config.get("instruments", {})
        strategy = self.config.get("strategy", {})

        # 验证必要参数
        if "threshold" not in strategy:
            print("❌ 缺少策略阈值参数")
            return False

        print("✅ 配置验证通过")
        return True

    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置文件保存成功: {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ 配置文件保存失败: {e}")
            return False


if __name__ == "__main__":
    parser = ConfigParser()
    config = parser.load_config()
    parser.validate_config()
    print("配置加载完成！")
