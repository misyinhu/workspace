#!/usr/bin/env python3
"""获取当前持仓"""

import json
from typing import List, Dict, Any, Optional
from ib_insync import IB


def get_positions(ib: Optional[IB] = None) -> List[Dict[str, Any]]:
    if ib is None:
        from client.ib_connection import get_ib_connection
        ib = get_ib_connection()
    
    positions = ib.positions()
    result = []
    for pos in positions:
        result.append({
            "symbol": pos.contract.symbol,
            "secType": pos.contract.secType,
            "exchange": pos.contract.exchange,
            "position": pos.position,
            "avgCost": pos.avgCost,
            "account": pos.account,
        })
    return result


def format_positions(ib: Optional[IB] = None) -> str:
    positions = get_positions(ib)
    
    if not positions:
        return "📊 当前无持仓"
    
    lines = ["**📊 当前持仓**\n"]
    for pos in positions:
        symbol = pos.get("symbol", "")
        sec_type = pos.get("secType", "")
        position = pos.get("position", 0)
        avg_cost = pos.get("avgCost", 0)
        
        if position == 0:
            continue
            
        position_str = f"{position:+.0f}" if position != int(position) else f"{int(position):+}"
        cost_str = f"{avg_cost:.2f}" if avg_cost else "N/A"
        
        lines.append(f"• {symbol} ({sec_type}): {position_str} @ {cost_str}")
    
    if len(lines) == 1:
        return "📊 当前无持仓"
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    print(json.dumps(get_positions(), indent=2, default=str))