import sys
sys.path.insert(0, "C:/projects/trading")
from okx.api import Trade

key = "7c1d51b0-0104-476c-90db-c6dff1f0b090"
secret = "AF8EB679F8AA4CE9A38C5069CB0737A7"
passphrase = "AbcD@1234"
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

t1 = Trade(key, secret, passphrase, "1", proxies=proxies)
r1 = t1.get_orders_history(instType="SPOT", limit="1")
print("flag=1 code:", r1.get("code"), "msg:", r1.get("msg"))

t0 = Trade(key, secret, passphrase, "0", proxies=proxies)
r0 = t0.get_orders_history(instType="SPOT", limit="1")
print("flag=0 code:", r0.get("code"), "msg:", r0.get("msg"))
