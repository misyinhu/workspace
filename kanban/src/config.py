"""Configuration module."""

import os
import yaml
from pathlib import Path


def _get_config_path() -> str:
    candidates = [
        Path(__file__).parent.parent.parent / "config" / "settings.yaml",
        Path("D:/projects/trading/config/settings.yaml"),
        Path("/Users/wang/.opencode/workspace/trading/config/settings.yaml"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(candidates[0])


_SHARED_CONFIG_PATH = _get_config_path()

TIMEFRAMES = ["1m", "5m", "30m", "4h", "1D"]
TIMEFRAME_LABELS = {
    "1m": "1分钟",
    "5m": "5分钟",
    "30m": "30分钟",
    "4h": "4小时",
    "1D": "日线",
}
TREND_EMOJI = {"up": "📈", "down": "📉", "neutral": "➡️"}
TREND_CN = {"up": "上涨", "down": "下跌", "neutral": "震荡"}
BIAS_CN = {"UP": "偏多", "DOWN": "偏空", "NEUTRAL": "中性"}


def load_shared_config() -> dict:
    try:
        if os.path.exists(_SHARED_CONFIG_PATH):
            with open(_SHARED_CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    except:
        pass
    return {}


config = load_shared_config()
QUANT_CORE_URL = config.get("quant_core", {}).get("url", "http://100.82.238.11:8005")
CLIENT_ID = config.get("quant_core", {}).get("client_id", "10")

# 套利分析参数
ARBITRAGE_DEFAULTS = {
    "zscore_threshold": 3.0,  # Z-Score 触发阈值
    "correlation_threshold": 0.8,  # 相关性触发阈值
    "rsi_divergence_threshold": 20,  # RSI 背离阈值
    "correlation_window": 20,  # 滚动相关性窗口
}


def get_secrets():
    """从 streamlit secrets 读取敏感配置，fallback 到环境变量"""
    try:
        import streamlit as st
        return st.secrets
    except Exception:
        pass
    
    # fallback 到环境变量
    class EnvSecrets:
        def get(self, key, default=""):
            return os.getenv(key, default)
    return EnvSecrets()


def get_okx_api_key() -> str:
    return get_secrets().get("OKX_API_KEY", "")

def get_okx_secret_key() -> str:
    return get_secrets().get("OKX_SECRET_KEY", "")

def get_okx_passphrase() -> str:
    return get_secrets().get("OKX_PASSPHRASE", "")
