import sys

sys.path.insert(0, "C:/projects/trading/kanban/src")
from tv import TV_HOST, TV_PORT

print(f"TV_HOST={TV_HOST}")
print(f"TV_PORT={TV_PORT}")

import yaml

with open("C:/projects/trading/config/settings.yaml") as f:
    cfg = yaml.safe_load(f)
print(f"Config tv_cdp: {cfg.get('tv_cdp', 'NOT FOUND')}")
