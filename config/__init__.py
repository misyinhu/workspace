#!/usr/bin/env python3
"""配置加载模块"""

import os
import yaml
from typing import Any, Dict

_config: Dict[str, Any] = {}
_query_only: bool = True


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载配置文件"""
    global _config

    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "settings.yaml")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f) or {}
            return _config
    except Exception as e:
        print(f"加载配置失败: {e}")
        return {}


def get(key: str, default: Any = None) -> Any:
    """获取配置值"""
    if not _config:
        load_config()

    keys = key.split(".")
    value = _config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    
    if value is not None:
        return value
    
    # 回退：从 environments 当前环境获取
    env_config = _config.get("environments", {}).get(_config.get("current", "local"), {})
    if "feishu" in key:
        feishu_config = env_config.get("feishu", {})
        sub_key = key.replace("feishu.", "")
        return feishu_config.get(sub_key, default)
    
    return default


def get_ibkr_host() -> str:
    """获取 IBKR 主机"""
    return get("ibkr.host", "127.0.0.1")


def get_ibkr_port() -> int:
    """获取 IB Gateway 端口"""
    # 优先从 environments 配置获取（支持本地/远程切换）
    env_config = get("environments", {}).get(get("current", "local"), {})
    if "ib_port" in env_config:
        return int(env_config["ib_port"])
    # 回退到 ibkr.port 配置
    return int(get("ibkr.port", 4001))


def _get_from_env(key: str, default: Any = None) -> Any:
    """从当前环境配置中获取值"""
    env_config = get("environments", {}).get(get("current", "local"), {})
    if key in env_config:
        return env_config[key]
    return default


def get_feishu_app_id() -> str:
    """获取飞书 App ID"""
    return _get_from_env("feishu", {}).get("app_id", get("feishu.app_id", ""))


def get_feishu_app_secret() -> str:
    """获取飞书 App Secret"""
    return _get_from_env("feishu", {}).get("app_secret", get("feishu.app_secret", ""))


def get_feishu_chat_id() -> str:
    """获取飞书 Chat ID"""
    return _get_from_env("feishu", {}).get("chat_id", get("feishu.chat_id", ""))


def is_query_only() -> bool:
    """是否仅查询模式"""
    global _query_only
    return _query_only


def set_query_only(mode: bool):
    """设置仅查询模式"""
    global _query_only
    _query_only = mode


def get_webhook_port() -> int:
    """获取 Webhook 端口"""
    return int(get("webhook.port", 5002))
