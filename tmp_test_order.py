import sys

sys.path.insert(0, "C:/projects/trading")
from okx.api import Trade

key = "7c1d51b0-0104-476c-90db-c6dff1f0b090"
secret = "AF8EB679F8AA4CE9A38C5069CB0737A7"
passphrase = "AbcD@1234"
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

t = Trade(key, secret, passphrase, "1", proxies=proxies)
r = t.set_order(instId="DOGE-USDT", tdMode="cash", side="buy", ordType="market", sz="1")
print(
    "code:",
    r.get("code"),
    "msg:",
    r.get("msg"),
    "ordId:",
    r.get("data", [{}])[0].get("ordId", ""),
)
