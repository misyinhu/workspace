"""
Feishu 飞书通知服务
发送 Z120 监控信号到飞书群
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path


class FeishuNotifier:
    """飞书通知器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self._load_config()
        self.token = None
        self.token_expires = 0

    def _load_config(self) -> Dict[str, Any]:
        """从 settings.yaml 加载配置文件"""
        import sys
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        try:
            from config import get_feishu_app_id, get_feishu_app_secret, get_feishu_chat_id, load_config, get
            load_config()
            return {
                "feishu": {
                    "app_id": get_feishu_app_id(),
                    "app_secret": get_feishu_app_secret(),
                    "chat_id": get_feishu_chat_id(),
                    "api_endpoint": get("feishu.api_endpoint", "https://open.feishu.cn/open-apis/im/v1/messages"),
                    "auth_endpoint": get("feishu.auth_endpoint", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"),
                    "timeout": get("feishu.timeout", 30),
                }
            }
        except Exception:
            return {}

    def _get_app_access_token(self) -> Optional[str]:
        """获取应用访问令牌"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}

        # 支持平铺和嵌套两种配置结构
        cfg = self.config.get("feishu", self.config)
        payload = {
            "app_id": cfg.get("app_id"),
            "app_secret": cfg.get("app_secret"),
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()
            if data.get("code") == 0:
                self.token = data.get("tenant_access_token")
                self.token_expires = time.time() + data.get("expire", 7200) - 60
                return self.token
            else:
                print(f"❌ 获取 Token 失败: {data}")
                return None
        except Exception as e:
            print(f"❌ 请求 Token 异常: {e}")
            return None

    def _ensure_token(self) -> bool:
        """确保 Token 有效"""
        if self.token is None or time.time() >= self.token_expires:
            return self._get_app_access_token() is not None
        return True

    def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """
        发送消息到飞书群

        Args:
            message: 消息内容
            chat_id: 聊天 ID，默认使用配置中的 chat_id

        Returns:
            是否发送成功
        """
        if not self._ensure_token():
            print("❌ 无法获取访问令牌")
            return False

        # 如果没有传入 chat_id，从配置中获取
        cfg = self.config.get("feishu", self.config)
        if not chat_id:
            chat_id = cfg.get("chat_id")

        if not chat_id:
            print("❌ chat_id 不能为空")
            return False

        url = cfg.get("api_endpoint", "https://open.feishu.cn/open-apis/im/v1/messages")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        params = {"receive_id_type": "chat_id"}
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": message}),
        }

        try:
            response = requests.post(
                url, headers=headers, params=params, json=payload, timeout=30
            )
            data = response.json()
            if data.get("code") == 0:
                print(f"✅ 消息发送成功")
                return True
            else:
                print(f"❌ 消息发送失败: {data}")
                return False
        except Exception as e:
            print(f"❌ 发送消息异常: {e}")
            return False

    def send_z120_signal(
        self,
        pair_name: str,
        signal_type: str,
        zscore: float,
        spread_value: float,
        mean: float,
        std: float,
        action: str,
    ) -> bool:
        """
        发送 Z120 交易信号

        Args:
            pair_name: 交易对名称
            signal_type: 信号类型 (OVERSOLD/OVERBOUGHT/NEUTRAL)
            zscore: Z120 值
            spread_value: 价差值
            mean: 均价
            std: 标准差
            action: 建议操作
        """
        emoji_map = {
            "OVERSOLD": "📈",
            "OVERBOUGHT": "📉",
            "NEUTRAL": "➡️",
        }
        emoji = emoji_map.get(signal_type, "📊")

        message = f"""{emoji} Z120 信号通知

交易对: {pair_name}
信号类型: {signal_type}
Z120 值: {zscore:.2f}
当前价差: {spread_value:.2f}
120周期均值: {mean:.2f}
120周期标准差: {std:.2f}
建议操作: {action}

时间: {time.strftime("%Y-%m-%d %H:%M:%S")}"""

        return self.send_message(message)


class Z120AlertManager:
    """Z120 警报管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.notifier = FeishuNotifier(config_path)
        self.last_alerts: Dict[str, Dict[str, Any]] = {}

    def check_and_notify(
        self,
        pair_name: str,
        signal: Dict[str, Any],
        spread_value: float,
        mean: float,
        std: float,
    ) -> bool:
        """
        检查信号并发送通知

        Args:
            pair_name: 交易对名称
            signal: 信号字典
            spread_value: 价差值
            mean: 均价
            std: 标准差

        Returns:
            是否发送了通知
        """
        signal_type = signal.get("signal")
        action = signal.get("action", "HOLD")

        if signal_type in ["OVERSOLD", "OVERBOUGHT"]:
            last_signal = self.last_alerts.get(pair_name, {}).get("signal")
            if last_signal == signal_type:
                return False

            self.last_alerts[pair_name] = {
                "signal": signal_type,
                "timestamp": time.time(),
            }

            zscore = signal.get("zscore", 0)
            return self.notifier.send_z120_signal(
                pair_name=pair_name,
                signal_type=signal_type,
                zscore=zscore,
                spread_value=spread_value,
                mean=mean,
                std=std,
                action=action,
            )

        return False
