#!/usr/bin/env python3
"""OKX 交易客户端"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from okx import Account, Trade, MarketData


def _load_config():
    for p in [Path(__file__).parent / "config.yaml", Path(__file__).parent.parent / "config" / "okx.yaml"]:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f)
    return {}


class OKXTrader:
    def __init__(self, flag: str = "2"):
        self.flag = flag

        env_key = os.getenv("OKX_API_KEY")
        if env_key:
            self.api_key = env_key
            self.secret = os.getenv("OKX_API_SECRET", "")
            self.passphrase = os.getenv("OKX_PASSPHRASE", "")
        else:
            config = _load_config()
            okx_config = config.get("okx", {})
            mode_map = {"1": "live", "2": "sim"}
            mode = mode_map.get(flag, "sim")
            creds_list = okx_config.get(mode, [])
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

        self.account = Account.AccountAPI(self.api_key, self.secret, self.passphrase, self.flag)
        self.trade = Trade.TradeAPI(self.api_key, self.secret, self.passphrase, self.flag)
        self.market = MarketData.MarketAPI()

    def set_leverage(self, inst_id: str, leverage: str, tdMode: str = "cross"):
        self.account.set_leverage(instId=inst_id, lever=leverage, mgnMode=tdMode)

    def get_balance(self):
        return self.account.get_account_balance()

    def get_ticker(self, inst_id: str):
        return self.market.get_ticker(instId=inst_id)
    
    def get_kline(self, inst_id: str, bar: str = "1h", limit: int = 100):
        return self.market.get_candlesticks(instId=inst_id, bar=bar, limit=str(limit))
    
    def get_history_kline(self, inst_id: str, bar: str = "1m", limit: int = 100, after: Optional[str] = None, before: Optional[str] = None):
        """获取历史K线 (2天前~3个月)"""
        return self.market.get_history_candlesticks(
            instId=inst_id,
            bar=bar,
            limit=str(limit),
            after=after,
            before=before
        )
    
    def get_ohlc(self, inst_id: str, bar: str = "1m", limit: int = 100):
        """获取OHLC数据 [时间, 开盘, 最高, 最低, 收盘, 量]"""
        data = self.get_kline(inst_id, bar=bar, limit=limit)
        if data.get("code") == "0" and data.get("data"):
            return [
                {
                    'time': int(c[0]),
                    'open': float(c[1]),
                    'high': float(c[2]),
                    'low': float(c[3]),
                    'close': float(c[4]),
                    'vol': float(c[5])
                }
                for c in data["data"]
            ]
        return []
    
    def calculate_atr(self, inst_id: str, period: int = 14, bar: str = "1h") -> Optional[float]:
        """计算ATR (Average True Range)"""
        ohlc = self.get_ohlc(inst_id, bar=bar, limit=period + 1)
        if len(ohlc) < period + 1:
            return None
        
        tr_values = []
        for i in range(1, len(ohlc)):
            high = ohlc[i]['high']
            low = ohlc[i]['low']
            prev_close = ohlc[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values)

    def place_order(
        self,
        inst_id: str,
        side: str,
        sz: str,
        ord_type: str = "market",
        tdMode: str = "cash",
        leverage: str = None,
    ):
        params = {
            "instId": inst_id,
            "tdMode": tdMode,
            "side": side,
            "ordType": ord_type,
            "sz": sz,
        }
        if leverage:
            params["leverage"] = leverage
        return self.trade.place_order(**params)

    def calc_quantity_from_usd(self, inst_id: str, usd_amount: float, leverage: int = 1) -> int:
        ticker = self.get_ticker(inst_id)
        if ticker.get("code") != "0" or not ticker.get("data"):
            raise ValueError(f"获取 {inst_id} 价格失败: {ticker}")
        last_price = float(ticker["data"][0]["last"])
        position_value = usd_amount * leverage
        quantity = int(position_value / last_price)
        if quantity < 1:
            quantity = 1
        return quantity

    def cancel_order(self, inst_id: str, ord_id: str):
        return self.trade.cancel_order(instId=inst_id, ordId=ord_id)


def get_client() -> "OKXTrader":
    return OKXTrader()
