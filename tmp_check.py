import sys
sys.path.insert(0, "C:/projects/trading")
from okx_client.okx_trader import OKXTrader
t = OKXTrader()
print("proxies:", t.proxies)
print("flag:", t.flag)
print("api_key:", t.api_key[:8] + "...")
