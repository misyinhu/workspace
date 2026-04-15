#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from notify.nl_parser import parse_trading_command

result1 = parse_trading_command('买入1手GC')
print('买入1手GC:', repr(result1))
if result1.get('quantity') is not None:
    print('Quantity type:', type(result1['quantity']), 'Value:', repr(result1['quantity']))

result2 = parse_trading_command('买入100股AAPL')
print('买入100股AAPL:', repr(result2))