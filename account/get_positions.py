#!/usr/bin/env python3
"""获取当前持仓 - 通过 HTTP 调用 webhook 的 /positions 端点"""

import json
import sys
import os

# 调用 webhook 的 /positions 端点
import urllib.request

try:
    req = urllib.request.Request(
        "http://127.0.0.1:5002/positions",
        method="GET",
        headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        
    if "error" in data:
        print(json.dumps({"error": data["error"]}, indent=2))
        sys.exit(1)
    
    # 转换为旧格式兼容
    result = []
    for p in data.get("positions", []):
        result.append({
            "symbol": p.get("symbol", ""),
            "secType": "FUT" if p.get("symbol", "").startswith(("GC", "MGC", "CL", "MNQ")) else "CRYPTO",
            "exchange": "",
            "position": p.get("position", 0),
            "avgCost": p.get("avgCost", 0),
            "account": "DUH583159",
        })
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}, indent=2))
    sys.exit(1)
