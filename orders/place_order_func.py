#!/usr/bin/env python3
"""下单交易 - 函数版本"""

import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from ib_insync import (
    IB,
    Stock,
    Future,
    CFD,
    Contract,
    Order,
    MarketOrder,
    LimitOrder,
    StopOrder,
    StopLimitOrder,
)


def get_position_contract(ib, symbol, action=None):
    try:
        positions = ib.positions()
        matching_positions = [pos for pos in positions if pos.contract.symbol == symbol]
        
        if not matching_positions:
            return None
        
        if len(matching_positions) == 1:
            return matching_positions[0].contract
        
        if action == "SELL":
            for pos in matching_positions:
                if pos.position > 0:
                    return pos.contract
        elif action == "BUY":
            for pos in matching_positions:
                if pos.position < 0:
                    return pos.contract
        
        return matching_positions[0].contract
    except:
        pass
    return None


def is_contract_expired(contract):
    expiry_str = contract.lastTradeDateOrContractMonth
    if not expiry_str:
        return False
    try:
        now = datetime.now()
        future_date = now + timedelta(days=30)
        future_day = future_date.year * 10000 + future_date.month * 100 + future_date.day
        expiry = int(expiry_str)
        return expiry < future_day
    except:
        return False


def select_main_contract(details, symbol, ib, prefer_position=True):
    if prefer_position:
        pos_contract = get_position_contract(ib, symbol)
        if pos_contract:
            if is_contract_expired(pos_contract):
                print(f"持仓合约 {pos_contract.localSymbol} 已/即将过期，使用主力合约")
            else:
                print(f"使用持仓合约: {pos_contract.localSymbol if hasattr(pos_contract, 'localSymbol') else pos_contract}")
                return pos_contract
    
    if not details:
        return None
    
    now = datetime.now()
    current_day = now.year * 10000 + now.month * 100 + now.day
    quarter_months = [3, 6, 9, 12]
    
    candidates = []
    for d in details:
        c = d.contract
        expiry_str = c.lastTradeDateOrContractMonth
        if expiry_str:
            try:
                expiry = int(expiry_str)
                if expiry < current_day + 30:
                    continue
                
                month = expiry % 100
                priority = 0
                if month in quarter_months:
                    priority = 3
                elif month == (now.month % 100) + 1:
                    priority = 2
                else:
                    priority = 1
                
                candidates.append((priority, expiry, c))
            except:
                pass
    
    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]))
        contract = candidates[0][2]
        print(f"主力合约: {contract.localSymbol if hasattr(contract, 'localSymbol') else contract}")
        return contract
    
    if details:
        contract = details[0].contract
        print(f"使用合约: {contract.localSymbol if hasattr(contract, 'localSymbol') else contract}")
        return contract
    
    return None


def place_order_with_retry(ib, contract, order, action, quantity):
    trade = ib.placeOrder(contract, order)
    ib.sleep(2)
    
    error_msg = ""
    for log in trade.log:
        if "Error" in log.message:
            error_msg = log.message
            break
    
    if "201" in error_msg or "321" in error_msg or "permission" in error_msg.lower() or "physical delivery" in error_msg.lower():
        print(f"下单失败({error_msg[:50]}...)，回退到主力合约...")
        
        symbol = contract.symbol
        base_contract = Future(symbol, exchange=contract.exchange, currency=contract.currency)
        details = ib.reqContractDetails(base_contract)
        main_contract = select_main_contract(details, symbol, ib, prefer_position=False)
        
        if main_contract:
            print(f"重试下单: {main_contract.localSymbol}")
            trade = ib.placeOrder(main_contract, order)
            ib.sleep(2)
            return trade, main_contract
    
    return trade, contract


def place_order(
    ib: IB,
    symbol: str,
    action: str,
    quantity: float,
    order_type: str = "MKT",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    sec_type: str = None,
    exchange: str = None,
    currency: str = "USD",
    use_main_contract: bool = True,
    close_position: bool = False,
    local_symbol: Optional[str] = None,
    conId: Optional[int] = None,
    outside_rth: bool = False,
    cash_quantity: Optional[float] = None,
    tif: str = "DAY",
) -> Dict[str, Any]:
    # 自动检测 sec_type 和 exchange
    futures = {"GC", "ES", "NQ", "YM", "ZB", "ZN"}
    crypto = {"BTC", "ETH", "DOGE"}
    if sec_type is None:
        sec_type = "FUT" if symbol in futures else "CRYPTO" if symbol in crypto else "STK"
    if exchange is None:
        if symbol == "GC":
            exchange = "COMEX"
        elif symbol in futures:
            exchange = "COMEX"
        elif symbol in crypto:
            exchange = "PAXOS"
        else:
            exchange = "SMART"
    
    result = {}
    
    try:
        import sys, traceback
        print(f"[DEBUG] Entering place_order: symbol={symbol}, action={action}, quantity={quantity}, sec_type={sec_type}, exchange={exchange}", file=sys.stderr)
        if close_position:
            positions = ib.positions()()
            matching_positions = [pos for pos in positions if pos.contract.symbol == symbol]
            
            if not matching_positions:
                return {"error": f"未找到 {symbol} 的持仓"}
            
            total_position = sum(pos.position for pos in matching_positions)
            
            if quantity is None:
                quantity = abs(int(total_position))
            
            if total_position > 0:
                action = "SELL"
            elif total_position < 0:
                action = "BUY"
            else:
                return {"error": f"{symbol} 净持仓为0，无需平仓"}
            
            pos_contract = get_position_contract(ib, symbol, action)
            
            if not pos_contract:
                return {"error": f"未找到 {symbol} 的持仓"}
            
            contract = pos_contract
            
            if contract.secType == "STK" and contract.exchange in ("ARCA", "NYSE", "NASDAQ"):
                contract = Stock(symbol, exchange="SMART", currency=contract.currency)
            elif contract.secType == "FUT" and not contract.exchange:
                local_symbol = getattr(contract, "localSymbol", None)
                if local_symbol:
                    contract = Contract(localSymbol=local_symbol, exchange="COMEX", secType="FUT", currency=contract.currency)
                elif contract.conId:
                    contract = Contract(conId=contract.conId, exchange="COMEX", secType="FUT", currency=contract.currency)
        elif sec_type == "FUT":
            if local_symbol:
                contract = Contract(localSymbol=local_symbol, exchange=exchange, secType="FUT", currency=currency)
            elif conId:
                contract = Contract(conId=conId)
            else:
                base_contract = Future(symbol, exchange=exchange, currency=currency)
                details = ib.reqContractDetails(base_contract)
                
                if use_main_contract:
                    contract = select_main_contract(details, symbol, ib)
                else:
                    contract = details[0].contract if details else base_contract
        elif sec_type == "CFD":
            contract = CFD(symbol, exchange=exchange, currency=currency)
        elif sec_type == "CMDTY":
            contract = Contract(symbol=symbol, secType="CMDTY", exchange="SMART", currency=currency)
        elif sec_type == "CRYPTO":
            contract = Contract(symbol=symbol, secType="CRYPTO", exchange=exchange or "PAXOS", currency=currency)
        else:
            contract = Stock(symbol, exchange=exchange, currency=currency)
        
        if sec_type == "CRYPTO" and cash_quantity:
            print(f"[DEBUG] Using CRYPTO cash quantity: {cash_quantity} USD", file=sys.stderr)
            order = Order()
            order.action = action
            order.orderType = order_type
            order.totalQuantity = 0
            order.cashQty = cash_quantity
            if order_type == "MKT":
                order.tif = "IOC"
            else:
                order.tif = tif
            order.outsideRth = outside_rth
        else:
            print(f"[DEBUG] Using regular quantity: {quantity} contracts", file=sys.stderr)
            order_kwargs = {"action": action, "totalQuantity": quantity}
            if order_type == "MKT":
                order = MarketOrder(**order_kwargs)
            elif order_type == "LMT":
                order = LimitOrder(limitPrice=limit_price, **order_kwargs)
            elif order_type == "STP":
                order = StopOrder(stopPrice=stop_price, **order_kwargs)
            elif order_type == "STP LMT":
                order = StopLimitOrder(limitPrice=limit_price, stopPrice=stop_price, **order_kwargs)
            else:
                order = MarketOrder(**order_kwargs)
            order.tif = tif
            order.outsideRth = outside_rth
        
        if use_main_contract:
            trade, used_contract = place_order_with_retry(ib, contract, order, action, quantity)
        else:
            trade = ib.placeOrder(contract, order)
            used_contract = contract
        
        ib.sleep(2)
        
        error_msg = ""
        for log in trade.log:
            if log.status in ("Cancelled", "Inactive") and log.message:
                if "Error" in log.message or "error" in log.message.lower():
                    error_msg = log.message
                    break
        
        if trade.orderStatus.status in ("Cancelled", "Inactive") or error_msg:
            result = {
                "orderId": trade.order.orderId if hasattr(trade.order, "orderId") else 0,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "orderType": order_type,
                "status": trade.orderStatus.status,
                "filled": 0,
                "error": error_msg if error_msg else "Order cancelled or failed",
                "message": "Order failed",
            }
        else:
            result = {
                "orderId": trade.order.orderId if hasattr(trade.order, "orderId") else 0,
                "symbol": used_contract.symbol if hasattr(used_contract, "symbol") else symbol,
                "action": action,
                "quantity": quantity,
                "orderType": order_type,
                "status": trade.orderStatus.status,
                "filled": trade.orderStatus.filled,
                "message": "Order submitted",
            }
    
    except Exception as e:
        result = {"error": str(e)}
    
    return result


def format_order_result(result: Dict[str, Any]) -> str:
    if "error" in result:
        return f"❌ 下单失败: {result['error']}"
    
    status_emoji = "✅" if result.get("status") == "Filled" else "⏳"
    return f"""🤖 **下单结果**

{status_emoji} 标的: {result.get('symbol')}
操作: {result.get('action')}
数量: {result.get('quantity')}
订单类型: {result.get('orderType')}
状态: {result.get('status')}
成交: {result.get('filled')}
订单ID: {result.get('orderId')}"""