#!/usr/bin/env python3
"""
DOGE/ETH 比率网格交易机器人 - WebSocket版
使用 WebSocket 实时推送价格

运行: python3 doge_eth_grid_ws.py

注意: 需要安装 pip install websockets
"""

import os
import json
import time
import asyncio
import statistics
import websockets
from datetime import datetime

# ============== 配置 ==============
CONFIG = {
    "DEMO": True,           
    "THRESHOLD": 0.015,    
    "HOLDING_PERIOD": 7200,
    "MARGIN": 400,          
    "LEVERAGE": 10,         
    "WS_URL": "wss://ws.okx.com:8443/ws/v5/public",
    "DOGE": "DOGE-USDT",
    "ETH": "ETH-USDT",
}

# ============== WebSocket 交易机器人 ==============
class WsGridBot:
    def __init__(self):
        self.mean_ratio = 0
        self.position = None
        self.entry_time = None
        self.entry_ratio = 0
        
        self.doge_price = 0
        self.eth_price = 0
        
    async def connect(self):
        """连接WebSocket"""
        subscribe_msg = {
            "op": "subscribe",
            "args": [
                f"tickers.{CONFIG['DOGE']}",
                f"tickers.{CONFIG['ETH']}"
            ]
        }
        
        async with websockets.connect(CONFIG["WS_URL"]) as ws:
            await ws.send(json.dumps(subscribe_msg))
            print("已订阅 DOGE-USDT 和 ETH-USDT 价格推送")
            
            async for message in ws:
                data = json.loads(message)
                
                # 处理价格数据
                if "data" in data and data["data"]:
                    for ticker in data["data"]:
                        inst_id = ticker.get("instId")
                        price = float(ticker.get("last", "0"))
                        
                        if inst_id == CONFIG["DOGE"]:
                            self.doge_price = price
                        elif inst_id == CONFIG["ETH"]:
                            self.eth_price = price
                    
                    # 检查信号
                    if self.doge_price > 0 and self.eth_price > 0:
                        await self.check_signal()
                
                # 心跳响应
                elif data.get("op") == "ping":
                    await ws.send(json.dumps({"op": "pong"}))
    
    async def check_signal(self):
        """检查交易信号"""
        ratio = self.eth_price / self.doge_price
        deviation = (ratio - self.mean_ratio) / self.mean_ratio
        deviation_pct = deviation * 100
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"DOGE:{self.doge_price:.5f} ETH:{self.eth_price:.2f} "
              f"比率:{ratio:.0f} 偏离:{deviation_pct:+.2f}%")
        
        # 入场信号
        if self.position is None:
            if deviation < -CONFIG["THRESHOLD"]:
                await self.enter("long_ratio", ratio)
            elif deviation > CONFIG["THRESHOLD"]:
                await self.enter("short_ratio", ratio)
        
        # 出场检查
        elif self.position:
            elapsed = time.time() - self.entry_time
            
            if elapsed >= CONFIG["HOLDING_PERIOD"]:
                await self.exit("时间到期")
            elif self.position == "long_ratio" and deviation >= -0.002:
                await self.exit("回归均值")
            elif self.position == "short_ratio" and deviation <= 0.002:
                await self.exit("回归均值")
    
    async def enter(self, pos_type, ratio):
        """入场"""
        print(f"\n[入场] {pos_type} 比率:{ratio:.0f}")
        
        total = CONFIG["MARGIN"] * CONFIG["LEVERAGE"]
        each = total / 2
        
        eth_qty = each / self.eth_price
        doge_qty = each / self.doge_price
        
        if pos_type == "long_ratio":
            print(f"做多DOGE: {doge_qty:.0f} 做空ETH: {eth_qty:.4f}")
        else:
            print(f"做空DOGE: {doge_qty:.0f} 做多ETH: {eth_qty:.4f}")
        
        self.position = pos_type
        self.entry_time = time.time()
        self.entry_ratio = ratio
    
    async def exit(self, reason):
        """出场"""
        ratio = self.eth_price / self.doge_price
        
        if self.position == "long_ratio":
            profit = (ratio - self.entry_ratio) / self.entry_ratio * 100
        else:
            profit = (self.entry_ratio - ratio) / self.entry_ratio * 100
        
        print(f"[出场] {reason} 比率:{ratio:.0f} 盈亏:{profit:+.2f}%\n")
        
        self.position = None
        self.entry_time = None
    
    async def run(self):
        """运行"""
        print("=" * 60)
        print("DOGE/ETH 比率网格交易机器人 (WebSocket版)")
        print("=" * 60)
        
        # 初始化均值
        print("使用默认均值: 21800 (需添加REST获取历史)")
        self.mean_ratio = 21800
        
        print("正在连接WebSocket...")
        
        try:
            await self.connect()
        except Exception as e:
            print(f"连接错误: {e}")
            print("请检查网络或使用轮询版本")

if __name__ == "__main__":
    bot = WsGridBot()
    asyncio.run(bot.run())
