import sys

sys.path.insert(0, "C:/projects/trading/kanban/src")
from tv import TV_HOST, TV_PORT, get_chart_targets, get_all_tv_indicators

print(f"TV_HOST={TV_HOST}")
print(f"TV_PORT={TV_PORT}")
print("Testing get_chart_targets...")
targets = get_chart_targets()
print(f"Targets: {targets}")
print("Testing get_all_tv_indicators...")
data = get_all_tv_indicators("30m")
print(f"Data: {data}")
