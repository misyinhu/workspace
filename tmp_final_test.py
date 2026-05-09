import sys
import os

sys.path.insert(0, "C:/projects/trading/notify")
sys.path.insert(0, "C:/projects/trading")

from okx_client.okx_trader import OKXTrader

t = OKXTrader()
print("flag:", t.flag)
print("proxies:", t.proxies)
print("api_key:", t.api_key[:10], "...")

r = t.place_order("DOGE-USDT", "buy", "1")
print("result code:", r.get("code"), "msg:", r.get("msg"))
