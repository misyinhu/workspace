import requests
import json
import time
import hmac
import base64

key = "7c1d51b0-0104-476c-90db-c6dff1f0b090"
secret = "AF8EB679F8AA4CE9A38C5069CB0737A7"
passphrase = "AbcD@1234"

url = "https://www.okx.com/api/v5/account/balance"


def get_timestamp():
    now = time.time()
    ms = int((now - int(now)) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S.", time.localtime(now)) + f"{ms:03d}Z"


timestamp = get_timestamp()
message = timestamp + "GET" + "/api/v5/account/balance"
signature = base64.b64encode(
    hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), digestmod="sha256"
    ).digest()
).decode("utf-8")

headers = {
    "OK-ACCESS-KEY": key,
    "OK-ACCESS-SIGN": signature,
    "OK-ACCESS-TIMESTAMP": timestamp,
    "OK-ACCESS-PASSPHRASE": passphrase,
    "x-simulated-trading": "1",
}

proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

try:
    resp = requests.get(url, headers=headers, proxies=proxies, timeout=10)
    print("code:", resp.status_code)
    print("body:", resp.text[:800])
except Exception as e:
    print("error:", str(e))
