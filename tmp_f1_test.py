import sys
sys.path.insert(0, "C:/projects/trading")
from okx_client.okx_trader import OKXTrader
t = OKXTrader(flag="1")
print("flag:", t.flag)
print("proxies:", t.proxies)
r = t.place_order("DOGE-USDT", "buy", "1")
print("code:", r.get("code"), "msg:", r.get("msg"), "ordId:", r.get("data", [{}])[0].get("ordId", ""))
