#!/usr/bin/env python3
"""简单规则匹配的自然语言交易指令解析"""

import re
from typing import Dict, Any

# 外汇品种列表（真正的外汇对，使用 CASH 类型，交易所 IDEALPRO）
FOREX_SYMBOLS = {
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD',
    'EURJPY', 'GBPJPY', 'EURGBP', 'EURAUD', 'GBPAUD',
}

# 商品品种列表（贵金属等，使用 CMDTY 类型）
CMDTY_SYMBOLS = {
    'XAUUSD',  # 黄金 vs USD
    'XAGUSD',  # 白银 vs USD
}

TRADING_PATTERNS = [
    # 平仓 patterns (优先匹配)
    (r"平掉(\S+?)(?:仓|位)$", "CLOSE"),
    (r"平仓(\d+)单元(\S+)$", "CLOSE"),  # 平仓1单元gc
    (r"平仓(\d+)手(\S+)$", "CLOSE"),    # 平仓1手gc
    (r"平仓(\S+)$", "CLOSE"),
    (r"清仓$", "CLOSE"),
    
    # 卖出/做空 patterns (支持"手"和"股")
    (r"卖空(\d+)单元(\S+)$", "SELL"),  # 卖空1单元gc
    (r"卖出(\d+)单元(\S+)$", "SELL"),  # 卖出1单元gc
    (r"做空(\d+)单元(\S+)$", "SELL"),  # 做空1单元gc
    (r"卖空(\d+)(?:手|股)(\S+)$", "SELL"),
    (r"做空(\d+)(?:手|股)(\S+)$", "SELL"),
    (r"卖出(\d+)(?:手|股)(\S+)$", "SELL"),
    (r"卖出(\S+)$", "SELL"),
    (r"做空(\S+)$", "SELL"),
    (r"卖(\d+)$", "SELL"),  # 卖1 = 卖1手GC
    
    # 买入 patterns (支持"手"和"股")
    (r"买入(\d+)单元(\S+)$", "BUY"),  # 买入1单元gc
    (r"做多(\d+)单元(\S+)$", "BUY"),   # 做多1单元gc
    (r"买入(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"做多(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"买(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"买入(\d+)$", "BUY"),  # 买入1 = 买1手GC
    (r"买入(\S+)$", "BUY"),
    (r"做多(\S+)$", "BUY"),
    (r"购买(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"购买(\S+)$", "BUY"),
]

QUERY_PATTERNS = [
    r"^查看持仓$",
    r"^查看账户$",
    r"^查看订单$",
    r"^查看成交$",
    r"^账户余额$",
    r"^当前持仓$",
]


def parse_trading_command(message: str) -> Dict[str, Any]:
    """解析交易命令 - 简单规则匹配"""
    msg = message.strip()
    msg_lower = msg.lower()
    
    # 检查是否是查询指令
    for pattern in QUERY_PATTERNS:
        if re.search(pattern, msg_lower):
            return {"action": "QUERY", "raw": msg}
    
    # 检查是否是交易指令
    for pattern, action in TRADING_PATTERNS:
        match = re.search(pattern, msg_lower)
        if match:
            result = {"action": action, "raw": msg}
            
            # 提取数量和 symbol
            groups = match.groups()
            quantity = None
            symbol = None
            
            for g in groups:
                if g and g.isdigit():
                    quantity = int(g)
                elif g and g.strip() and not g.strip().isdigit():
                    symbol = g.strip()
            
            if quantity is not None:
                result["quantity"] = quantity
            if symbol:
                # 清理 symbol - 移除 "单元"、"手"、"股" 等后缀
                symbol = symbol.upper().strip()
                symbol = re.sub(r"(单元|手|股)$", "", symbol)
                symbol = symbol.strip()
                
                symbol_map = {
                    "BTC": "BTC", "比特币": "BTC",
                    "黄金": "GC", "黄金": "GC",
                    "小纳指": "MNQ", "纳指": "NQ",
                    "标普": "ES", "道指": "YM",
                }
                for k, v in symbol_map.items():
                    if k in symbol:
                        symbol = v
                        break
                result["symbol"] = symbol
                
                # 检测品种类型
                if symbol in CMDTY_SYMBOLS:
                    result["sec_type"] = "CMDTY"
                    result["exchange"] = "SMART"
                elif symbol in FOREX_SYMBOLS:
                    result["sec_type"] = "CASH"
                    result["exchange"] = "IDEALPRO"
            
            return result
    
    return {"action": "UNKNOWN", "raw": msg}


if __name__ == "__main__":
    test_cases = [
        "平掉BTC仓位",
        "平仓GC",
        "买入1手GC",
        "卖空2手NQ",
        "查看持仓",
        "今天天气怎么样",
    ]
    
    for msg in test_cases:
        result = parse_trading_command(msg)
        print(f"{msg} -> {result}")