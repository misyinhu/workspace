import sys

sys.path.insert(0, "C:/projects/trading/kanban/src")
from tv import run_tv_cmd, TV_HOST, TV_PORT

print(f"TV_HOST={TV_HOST}, TV_PORT={TV_PORT}")

result = run_tv_cmd(["symbol"])
print(f"Result: {result}")
print(f"Type: {type(result)}")
