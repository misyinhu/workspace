#!/usr/bin/env python3
"""OKX 交易客户端"""

import os
import sys
from typing import Optional

from okx import Account, Trade, MarketData


class OKXTrader:
    def __init__(self, flag: str = "0"):
        self.api_key = os.getenv("OKX_API_KEY")
        self.secret = os.getenv("OKX_API_SECRET")
        self.passphrase = os.getenv("OKX_PASSPHRASE")
        self.flag = flag

        if not all([self.api_key, self.secret, self.passphrase]):
            raise ValueError("请设置环境变量: OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE")

        self.account = Account.AccountAPI(self.api_key, self.secret, self.passphrase, self.flag)
        self.trade = Trade.TradeAPI(self.api_key, self.secret, self.passphrase, self.flag)
        self.market = MarketData.MarketAPI()

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

    def place_order(self, inst_id: str, side: str, sz: str, ord_type: str = "market"):
        return self.trade.place_order(
            instId=inst_id,
            tdMode="cash",
            side=side,
            ordType=ord_type,
            sz=sz
        )

    def cancel_order(self, inst_id: str, ord_id: str):
        return self.trade.cancel_order(instId=inst_id, ordId=ord_id)


def get_client() -> "OKXTrader":
    return OKXTrader()
