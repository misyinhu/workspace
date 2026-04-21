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
    (r"平仓(\d+)单元(\S+)$", "CLOSE"),
    (r"平仓(\d+)手(\S+)$", "CLOSE"),
    (r"平仓(\S+)(\d+)单元$", "CLOSE"),
    (r"平仓(\S+)(\d+)手$", "CLOSE"),
    (r"平仓(\S+)$", "CLOSE"),
    (r"清仓$", "CLOSE"),
    (r"(卖出|卖空|做空)(\d+)美元(\S+?)$", "SELL"),
    (r"(买入|买|做多)(\d+)美元(\S+?)$", "BUY"),
    
    # 卖出/做空 patterns (支持"手"和"股")
    (r"卖空(\d+)单元(\S+)$", "SELL"),
    (r"卖出(\d+)单元(\S+)$", "SELL"),
    (r"做空(\d+)单元(\S+)$", "SELL"),
    (r"卖空(\S+)(\d+)单元$", "SELL"),
    (r"卖出(\S+)(\d+)单元$", "SELL"),
    (r"做空(\S+)(\d+)单元$", "SELL"),
    (r"卖空(\S+)(\d+)手$", "SELL"),
    (r"卖出(\S+)(\d+)手$", "SELL"),
    (r"做空(\S+)(\d+)手$", "SELL"),
    (r"卖空(\d+)(?:手|股)(\S+)$", "SELL"),
    (r"做空(\d+)(?:手|股)(\S+)$", "SELL"),
    (r"卖出(\d+)(?:手|股)(\S+)$", "SELL"),
    (r"卖出(\S+)$", "SELL"),
    (r"做空(\S+)$", "SELL"),
    (r"卖(\d+)$", "SELL"),
    
    # 买入 patterns (支持"手"和"股")
    (r"买入(\d+)单元(\S+)$", "BUY"),
    (r"做多(\d+)单元(\S+)$", "BUY"),
    (r"买入(\S+)(\d+)单元$", "BUY"),
    (r"做多(\S+)(\d+)单元$", "BUY"),
    (r"买入(\S+)(\d+)手$", "BUY"),
    (r"做多(\S+)(\d+)手$", "BUY"),
    (r"买入(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"做多(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"买(\d+)(?:手|股)(\S+)$", "BUY"),
    (r"买入(\d+)$", "BUY"),
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
    msg = message.strip()
    msg_lower = msg.lower()
    
    for pattern in QUERY_PATTERNS:
        if re.search(pattern, msg_lower):
            return {"action": "QUERY", "raw": msg}
    
    for pattern, action in TRADING_PATTERNS:
        match = re.search(pattern, msg_lower)
        if match:
            result = {"action": action, "raw": msg}
            groups = match.groups()
            quantity = None
            symbol = None
            usd_amount = None
            
            if "美元" in pattern:
                for g in groups:
                    if g and g.isdigit():
                        usd_amount = int(g)
                    elif g and g.strip() and not g.strip().isdigit():
                        symbol = g.strip()
                if usd_amount:
                    result["usd_amount"] = usd_amount
            else:
                for g in groups:
                    if g and g.isdigit():
                        quantity = int(g)
                    elif g and g.strip() and not g.strip().isdigit():
                        symbol = g.strip()
                if quantity is not None:
                    result["quantity"] = quantity
            
            if symbol:
                symbol = symbol.upper().strip()
                symbol = re.sub(r"(单元|手|股)$", "", symbol)
                symbol = symbol.strip()
                
                if "-SWAP" not in symbol and any(k in symbol for k in ["DOGE", "ETH", "BTC"]):
                    symbol = symbol + "-USDT-SWAP"
                    result["exchange"] = "OKX"
                    result["sec_type"] = "SWAP"
                else:
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
                    if symbol in CMDTY_SYMBOLS:
                        result["sec_type"] = "CMDTY"
                        result["exchange"] = "SMART"
                    elif symbol in FOREX_SYMBOLS:
                        result["sec_type"] = "CASH"
                        result["exchange"] = "IDEALPRO"
                
                result["symbol"] = symbol
            
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