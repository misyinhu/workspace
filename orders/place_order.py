#!/usr/bin/env python3
"""下单交易"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 确保使用正确的 Python 环境（虚拟环境支持）
try:
    from config.env_config import ensure_venv
    ensure_venv()
except ImportError:
    pass  # 如果 env_config 不存在，继续执行

import json
import argparse
from datetime import datetime
from ib_insync import (
    IB,
    Stock,
    Future,
    CFD,
    MarketOrder,
    LimitOrder,
    StopOrder,
    StopLimitOrder,
    Contract,
    Order,
)

from client.ibkr_client import get_client_id, IBKR_HOST, IBKR_PORT


def get_position_contract(ib, symbol, action=None):
    """查询持仓中是否有该 symbol 的合约，支持多合约选择"""
    try:
        positions = ib.positions()
        matching_positions = []

        for pos in positions:
            if pos.contract.symbol == symbol:
                matching_positions.append(pos)

        if not matching_positions:
            return None

        # 如果只有一个匹配，直接返回
        if len(matching_positions) == 1:
            return matching_positions[0].contract

        # 如果有多个匹配，根据action选择合适的合约
        if action == "SELL":
            # 卖出时优先选择多头持仓（平多头）
            for pos in matching_positions:
                if pos.position > 0:
                    return pos.contract
        elif action == "BUY":
            # 买入时优先选择空头持仓（平空头）
            for pos in matching_positions:
                if pos.position < 0:
                    return pos.contract

        # 如果没有找到匹配方向的，返回第一个
        return matching_positions[0].contract

    except:
        pass
    return None


def is_contract_expired(contract):
    """检查合约是否已过期或即将过期（30天内）"""
    expiry_str = contract.lastTradeDateOrContractMonth
    if not expiry_str:
        return False
    try:
        from datetime import timedelta

        now = datetime.now()
        # 正确计算30天后的日期
        future_date = now + timedelta(days=30)
        future_day = (
            future_date.year * 10000 + future_date.month * 100 + future_date.day
        )
        expiry = int(expiry_str)
        # 如果合约在30天内到期，返回True（表示即将过期）
        return expiry < future_day
    except:
        return False


def select_main_contract(details, symbol, ib, prefer_position=True):
    """选择合约：优先返回持仓中的合约，其次选择主力合约"""

    # 1. 优先检查是否有持仓
    if prefer_position:
        pos_contract = get_position_contract(ib, symbol)
        if pos_contract:
            # 检查持仓合约是否已过期
            if is_contract_expired(pos_contract):
                print(f"持仓合约 {pos_contract.localSymbol} 已/即将过期，使用主力合约")
            else:
                print(
                    f"使用持仓合约: {pos_contract.localSymbol if hasattr(pos_contract, 'localSymbol') else pos_contract}"
                )
                return pos_contract

    # 2. 选择主力合约（非最近月）
    if not details:
        return None

    now = datetime.now()
    current_day = now.year * 10000 + now.month * 100 + now.day

    # 季月月份（3,6,9,12）
    quarter_months = [3, 6, 9, 12]

    candidates = []
    for d in details:
        c = d.contract
        expiry_str = c.lastTradeDateOrContractMonth
        if expiry_str:
            try:
                expiry = int(expiry_str)
                # 跳过30天内到期的合约（避免实物交割问题）
                if expiry < current_day + 30:
                    continue

                # 计算月份
                month = expiry % 100

                # 主力合约优先级：季月 > 下月 > 其他
                priority = 0
                if month in quarter_months:
                    priority = 3  # 季月最高优先级
                elif month == (now.month % 100) + 1:
                    priority = 2  # 下次月
                else:
                    priority = 1

                candidates.append((priority, expiry, c))
            except:
                pass

    if candidates:
        # 选择优先级最高、离现在最近的
        candidates.sort(key=lambda x: (x[0], x[1]))
        contract = candidates[0][2]
        print(
            f"主力合约: {contract.localSymbol if hasattr(contract, 'localSymbol') else contract}"
        )
        return contract

    contract = details[0].contract
    if details:
        contract = details[0].contract
        print(
            f"使用合约: {contract.localSymbol if hasattr(contract, 'localSymbol') else contract}"
        )
        return contract

    return None


def parse_args():
    parser = argparse.ArgumentParser(description="下单交易")
    parser.add_argument("--symbol")
    parser.add_argument("--action", choices=["BUY", "SELL"])
    parser.add_argument("--quantity", type=float)
    parser.add_argument(
        "--cash_quantity",
        type=float,
        help="现金数量（加密货币专用，表示美元金额）",
    )
    parser.add_argument("--order_type", default="MKT")
    parser.add_argument("--limit_price", type=float)
    parser.add_argument("--stop_price", type=float)
    parser.add_argument("--tif", default="DAY")
    parser.add_argument("--exchange", default="SMART")
    parser.add_argument("--sec_type", default="STK")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--conId", type=int)
    parser.add_argument("--local_symbol")
    parser.add_argument("--outside_rth", action="store_true")
    parser.add_argument(
        "--use_main_contract",
        action="store_true",
        help="自动选择主力合约（优先持仓合约，失败则回退到主力合约）",
    )
    parser.add_argument(
        "--close_position",
        action="store_true",
        help="自动平仓模式：根据持仓方向自动决定BUY或SELL，选择持仓合约，默认全平",
    )

    args = parser.parse_args()

    # 验证参数组合
    if args.close_position:
        # 自动平仓模式：不需要指定action
        args.action = None  # 稍后会根据持仓自动设置
    elif args.action is None:
        # 如果不是自动平仓，必须指定action
        parser.error("--action 是必需的，除非使用 --close_position")

    return args


def place_order_with_retry(ib, contract, order, action, quantity):
    """下单，失败时回退到主力合约重试"""
    trade = ib.placeOrder(contract, order)

    # 等待一下让订单状态更新
    ib.sleep(2)

    # 检查订单 log 获取最终状态
    error_msg = ""
    for log in trade.log:
        if "Error" in log.message:
            error_msg = log.message
            break

    # 如果是因为权限/交割问题（Error 201, 321），回退到主力合约
    if (
        "201" in error_msg
        or "321" in error_msg
        or "permission" in error_msg.lower()
        or "physical delivery" in error_msg.lower()
    ):
        print(f"下单失败({error_msg[:50]}...)，回退到主力合约...")

        # 获取主力合约（不使用持仓）
        symbol = contract.symbol
        base_contract = Future(
            symbol, exchange=contract.exchange, currency=contract.currency
        )
        details = ib.reqContractDetails(base_contract)
        main_contract = select_main_contract(details, symbol, ib, prefer_position=False)

        if main_contract:
            print(f"重试下单: {main_contract.localSymbol}")
            trade = ib.placeOrder(main_contract, order)
            ib.sleep(2)
            return trade, main_contract

    return trade, contract


def main():
    args = parse_args()

    ib = IB()
    result = {}

    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

        # 创建合约
        if args.close_position:
            symbol = args.symbol

            # 查询所有匹配的持仓
            positions = ib.positions()
            matching_positions = [
                pos for pos in positions if pos.contract.symbol == symbol
            ]

            if not matching_positions:
                raise ValueError(f"未找到 {symbol} 的持仓")

            # 自动决定action和quantity
            total_position = sum(pos.position for pos in matching_positions)

            # 如果没有指定quantity，默认全平
            if args.quantity is None:
                args.quantity = abs(int(total_position))
                print(f"📊 自动计算平仓数量: {args.quantity}手")

            if total_position > 0:
                args.action = "SELL"  # 平多头
                print(
                    f"🔍 检测到 {symbol} 多头持仓 {total_position}手，自动执行SELL平仓 {args.quantity}手"
                )
            elif total_position < 0:
                args.action = "BUY"  # 平空头
                print(
                    f"🔍 检测到 {symbol} 空头持仓 {abs(total_position)}手，自动执行BUY平仓 {args.quantity}手"
                )
            else:
                raise ValueError(f"{symbol} 净持仓为0，无需平仓")

            # 选择持仓合约
            pos_contract = get_position_contract(ib, symbol, args.action)

            if pos_contract:
                contract = pos_contract
                print(
                    f"使用持仓合约: {contract.localSymbol if hasattr(contract, 'localSymbol') else contract}"
                )

                # 股票使用SMART路由
                if contract.secType == "STK" and contract.exchange in (
                    "ARCA",
                    "NYSE",
                    "NASDAQ",
                ):
                    print(f"股票使用SMART路由避免10311错误")
                    contract = Stock(
                        symbol, exchange="SMART", currency=contract.currency
                    )
                    print(f"使用合约: {contract}")

                # 期货如果exchange为空，使用COMEX交易所
                elif contract.secType == "FUT" and not contract.exchange:
                    print(f"期货exchange为空，使用COMEX交易所")
                    # 保留原来的localSymbol
                    local_symbol = getattr(contract, "localSymbol", None)
                    if local_symbol:
                        print(f"使用原合约localSymbol: {local_symbol}")
                        contract = Contract(
                            localSymbol=local_symbol,
                            exchange="COMEX",
                            secType="FUT",
                            currency=contract.currency,
                        )
                    else:
                        # 如果没有localSymbol，使用conId
                        if contract.conId:
                            print(f"使用原合约conId: {contract.conId}")
                            contract = Contract(
                                conId=contract.conId,
                                exchange="COMEX",
                                secType="FUT",
                                currency=contract.currency,
                            )
                    print(f"使用合约: {contract}")
            else:
                raise ValueError(f"未找到 {symbol} 的持仓")
        elif args.sec_type == "FUT":
            if args.local_symbol:
                contract = Contract(
                    localSymbol=args.local_symbol,
                    exchange=args.exchange,
                    secType="FUT",
                    currency=args.currency,
                )
            elif args.conId:
                contract = Contract(conId=args.conId)
            else:
                symbol = args.symbol or "GC"
                base_contract = Future(
                    symbol, exchange=args.exchange, currency=args.currency
                )
                details = ib.reqContractDetails(base_contract)

                if args.use_main_contract:
                    contract = select_main_contract(details, symbol, ib)
                else:
                    contract = details[0].contract if details else base_contract
                    print(
                        f"使用合约: {contract.localSymbol if hasattr(contract, 'localSymbol') else contract}"
                    )
        elif args.sec_type == "CFD":
            contract = CFD(args.symbol, exchange=args.exchange, currency=args.currency)
        elif args.sec_type == "CMDTY":
            contract = Contract(
                symbol=args.symbol,
                secType="CMDTY",
                exchange="SMART",
                currency=args.currency,
            )
        elif args.sec_type == "CRYPTO":
            contract = Contract(
                symbol=args.symbol,
                secType="CRYPTO",
                exchange=args.exchange or "PAXOS",
                currency=args.currency,
            )
        else:
            contract = Stock(
                args.symbol, exchange=args.exchange, currency=args.currency
            )

        # 创建订单
        if args.sec_type == "CRYPTO" and args.cash_quantity:
            # 加密货币现金订单 - 必须使用 Order() 直接创建
            order = Order()
            order.action = args.action
            order.orderType = args.order_type
            order.totalQuantity = 0  # 不指定数量，使用 cashQty
            order.cashQty = args.cash_quantity
            if args.order_type == "MKT":
                order.tif = "IOC"  # 加密货币 MKT 只支持 IOC
            else:
                order.tif = args.tif
            order.outsideRth = args.outside_rth
        else:
            # 普通订单
            order_kwargs = {"action": args.action, "totalQuantity": args.quantity}
            if args.order_type == "MKT":
                order = MarketOrder(**order_kwargs)
            elif args.order_type == "LMT":
                order = LimitOrder(limitPrice=args.limit_price, **order_kwargs)
            elif args.order_type == "STP":
                order = StopOrder(stopPrice=args.stop_price, **order_kwargs)
            elif args.order_type == "STP LMT":
                order = StopLimitOrder(
                    limitPrice=args.limit_price, stopPrice=args.stop_price, **order_kwargs
                )
            else:
                order = MarketOrder(**order_kwargs)
            order.tif = args.tif
            order.outsideRth = args.outside_rth

        # 下单（带回退机制）
        if args.use_main_contract:
            trade, used_contract = place_order_with_retry(
                ib, contract, order, args.action, args.quantity
            )
        else:
            trade = ib.placeOrder(contract, order)
            used_contract = contract

        # 处理 10311 错误（直接传递限制）- 自动回退到 SMART 路由
        if trade.orderStatus.status == "Cancelled":
            error_msg = ""
            for log in trade.log:
                if "10311" in log.message:
                    error_msg = log.message
                    break

            if error_msg and used_contract.secType == "STK":
                print(f"10311 错误，回退到 SMART 路由...")

                # 回退到 SMART 路由
                if args.use_main_contract:
                    contract = Stock(
                        used_contract.symbol,
                        exchange="SMART",
                        currency=used_contract.currency,
                    )
                else:
                    contract = Stock(
                        args.symbol, exchange="SMART", currency=args.currency
                    )

                print(f"使用合约: {contract}")
                trade = ib.placeOrder(contract, order)
                used_contract = contract

        # 检查下单是否成功
        ib.sleep(2)

        # 检查错误
        error_msg = ""
        for log in trade.log:
            if log.status in ("Cancelled", "Inactive") and log.message:
                if "Error" in log.message or "error" in log.message.lower():
                    error_msg = log.message
                    break

        # 检查订单状态
        if trade.orderStatus.status in ("Cancelled", "Inactive") or error_msg:
            result = {
                "orderId": trade.order.orderId
                if hasattr(trade.order, "orderId")
                else 0,
                "symbol": args.symbol,
                "action": args.action,
                "quantity": args.quantity,
                "orderType": args.order_type,
                "status": trade.orderStatus.status,
                "filled": 0,
                "error": error_msg if error_msg else "Order cancelled or failed",
                "message": "Order failed",
            }
        else:
            result = {
                "orderId": trade.order.orderId
                if hasattr(trade.order, "orderId")
                else 0,
                "symbol": used_contract.symbol
                if hasattr(used_contract, "symbol")
                else args.symbol,
                "action": args.action,
                "quantity": args.quantity,
                "orderType": args.order_type,
                "status": trade.orderStatus.status,
                "filled": trade.orderStatus.filled,
                "message": "Order submitted",
            }

    except Exception as e:
        result = {"error": str(e)}
    finally:
        if ib.isConnected():
            ib.disconnect()

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
