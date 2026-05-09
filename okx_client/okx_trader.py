#!/usr/bin/env python3
"""OKX 交易客户端"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml
import okx

_version = getattr(okx, "__version__", "unknown")

if _version.startswith("2."):
    from okx.api import Account, Trade, Market

    AccountAPI = Account
    TradeAPI = Trade
    MarketAPI = Market
else:
    from okx.account import Account
    from okx.trade import Trade
    from okx.market import Market

    AccountAPI = Account
    TradeAPI = Trade
    MarketAPI = Market

# Map YAML flag value to SDK flag number
_SDK_FLAG_MAP = {"sim": "1", "live": "2"}


def _load_config():
    for p in [
        Path(__file__).parent / "config.yaml",
        Path(__file__).parent.parent / "config" / "okx.yaml",
    ]:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f)
    return {}


class OKXTrader:
    def __init__(self, flag: Optional[str] = None, proxies: Optional[dict] = None):
        if proxies is None:
            http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
            https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
            if not http_proxy and not https_proxy:
                proxies = {
                    "http": "http://127.0.0.1:7890",
                    "https": "http://127.0.0.1:7890",
                }
            elif http_proxy or https_proxy:
                proxies = {
                    "http": http_proxy or https_proxy,
                    "https": https_proxy or http_proxy,
                }
            else:
                proxies = {}
        self.proxies = proxies

        env_key = os.getenv("OKX_API_KEY")
        if env_key:
            self.api_key = env_key
            self.secret = os.getenv("OKX_API_SECRET", "")
            self.passphrase = os.getenv("OKX_PASSPHRASE", "")
            self.flag = os.getenv("OKX_FLAG", "1")
        else:
            config = _load_config()
            okx_config = config.get("okx", {})
            yaml_flag = flag or okx_config.get("flag", "sim")
            self.flag = _SDK_FLAG_MAP.get(yaml_flag, "1")
            creds_list = okx_config.get(yaml_flag, [])
            if creds_list:
                creds = creds_list[0] if isinstance(creds_list, list) else creds_list
                self.api_key = creds.get("apikey", "")
                self.secret = creds.get("secretkey", "")
                self.passphrase = creds.get("passphrase", "")
            else:
                self.api_key = ""
                self.secret = ""
                self.passphrase = ""

        if not all([self.api_key, self.secret, self.passphrase]):
            raise ValueError(f"OKX 密钥未配置 (flag={flag})")

        self.account = AccountAPI(
            self.api_key, self.secret, self.passphrase, self.flag
        )
        self.trade = TradeAPI(
            self.api_key, self.secret, self.passphrase, self.flag
        )
        self.market = MarketAPI()

    def set_leverage(self, inst_id: str, leverage: str, tdMode: str = "cross"):
        self.account.set_leverage(instId=inst_id, lever=leverage, mgnMode=tdMode)

    def get_balance(self):
        return self.account.get_balance()

    def get_ticker(self, inst_id: str):
        return self.market.get_ticker(instId=inst_id)

    def get_kline(self, inst_id: str, bar: str = "1h", limit: int = 100):
        return self.market.get_candlesticks(instId=inst_id, bar=bar, limit=str(limit))

    def get_history_kline(
        self,
        inst_id: str,
        bar: str = "1m",
        limit: int = 100,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ):
        return self.market.get_history_candlesticks(
            instId=inst_id, bar=bar, limit=str(limit), after=after, before=before
        )

    def get_ohlc(self, inst_id: str, bar: str = "1m", limit: int = 100):
        data = self.get_kline(inst_id, bar=bar, limit=limit)
        if data.get("code") == "0" and data.get("data"):
            return [
                {
                    "time": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                }
                for c in data["data"]
            ]
        return []

    def place_order(
        self,
        inst_id: str,
        side: str,
        sz: str,
        ord_type: str = "market",
        tdMode: str = "cash",
        posSide: Optional[str] = None,
    ):
        params = {
            "instId": inst_id,
            "tdMode": tdMode,
            "side": side,
            "ordType": ord_type,
            "sz": sz,
        }
        if posSide:
            params["posSide"] = posSide
        return self.trade.set_order(**params)

    def calc_quantity_from_usd(
        self, inst_id: str, usd_amount: float, leverage: int = 1
    ) -> float:
        ticker = self.get_ticker(inst_id)
        if ticker.get("code") != "0" or not ticker.get("data"):
            raise ValueError(f"获取 {inst_id} 价格失败: {ticker}")
        last_price = float(ticker["data"][0]["last"])
        position_value = usd_amount * leverage
        doge_qty = position_value / last_price
        contract_size = 1000
        qty = round(doge_qty / contract_size) * contract_size
        return max(qty, float(ticker["data"][0].get("minSz", 1)))

    def close_position(self, inst_id: str, posSide: str = "long"):
        return self.trade.close_position(instId=inst_id, posSide=posSide)

    def get_positions(self, inst_type: str = "SPOT"):
        return self.account.get_positions(instType=inst_type)
