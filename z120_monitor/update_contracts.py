#!/usr/bin/env python3
"""
自动更新 pairs.yaml 中的 local_symbol
检查合约是否 < 30天到期，如果是则更新为新主力合约
"""

import os
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PAIRS_FILE = PROJECT_ROOT / "z120_monitor" / "config" / "pairs.yaml"


def get_main_contract(symbol: str, exchange: str, currency: str) -> tuple:
    """获取主力合约的 localSymbol 和到期日"""
    try:
        import nest_asyncio
        nest_asyncio.apply()
        from ib_insync import IB, Future
        import asyncio
        
        async def fetch():
            ib = IB()
            await ib.connectAsync('127.0.0.1', 4001, clientId=99)
            
            contracts = ib.reqContractDetails(Future(symbol=symbol, exchange=exchange, currency=currency))
            if not contracts:
                return None, None
            
            # 选择最近到期的合约（跳过7天内到期的）
            now = datetime.now()
            current_day = now.year * 10000 + now.month * 100 + now.day
            
            candidates = []
            for d in contracts:
                c = d.contract
                expiry_str = c.lastTradeDateOrContractMonth
                if expiry_str:
                    try:
                        expiry = int(expiry_str)
                        if expiry > current_day + 7:  # 跳过7天内到期
                            candidates.append((expiry, c.localSymbol))
                    except:
                        continue
            
            if candidates:
                candidates.sort()  # 按到期日升序
                return candidates[0][1], candidates[0][0]
            
            ib.disconnect()
            return None, None
        
        return asyncio.run(fetch())
    except Exception as e:
        print(f"获取合约失败: {e}")
        return None, None


def check_and_update_contracts():
    """检查并更新所有合约"""
    print(f"🔍 检查合约更新 ({datetime.now().strftime('%Y-%m-%d')})")
    
    with open(PAIRS_FILE) as f:
        config = yaml.safe_load(f)
    
    now = datetime.now()
    current_day = now.year * 10000 + now.month * 100 + now.day
    updated = False
    
    for pair in config.get("pairs", []):
        for asset in pair.get("assets", []):
            local_symbol = asset.get("local_symbol", "")
            symbol = asset.get("symbol", "")
            exchange = asset.get("exchange", "")
            currency = asset.get("currency", "USD")
            
            if not local_symbol or asset.get("sec_type") != "FUT":
                continue
            
            # 解析当前合约到期日
            # local_symbol 格式如 "MNQH6" -> 202603
            try:
                month_code = local_symbol[-2:-1]  # H, M, U, Z
                year_code = local_symbol[-1]      # 6, 7, 8
                
                month_map = {'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
                            'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12}
                month = month_map.get(month_code, 0)
                year = 2020 + int(year_code)
                expiry = year * 10000 + month * 100 + 1
                
                days_to_expiry = (datetime(year, month, 1) - now).days
                
                if days_to_expiry < 30:
                    print(f"  ⚠️ {local_symbol} ({symbol}) 将在 {days_to_expiry} 天后到期")
                    
                    # 获取新主力合约
                    new_symbol, new_expiry = get_main_contract(symbol, exchange, currency)
                    if new_symbol and new_symbol != local_symbol:
                        print(f"  🔄 更新: {local_symbol} -> {new_symbol}")
                        asset["local_symbol"] = new_symbol
                        updated = True
                    else:
                        print(f"  ❌ 无法获取新合约")
                else:
                    print(f"  ✅ {local_symbol} ({symbol}) 还有 {days_to_expiry} 天到期")
                    
            except Exception as e:
                print(f"  ❌ 解析 {local_symbol} 失败: {e}")
    
    if updated:
        with open(PAIRS_FILE, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print("✅ pairs.yaml 已更新")
    else:
        print("✅ 无需更新")
    
    return updated


if __name__ == "__main__":
    check_and_update_contracts()
