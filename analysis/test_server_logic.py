# Test what the server should be returning
import sys
sys.path.append('.')

import db

# Test the actual db function
bot_name = 'hybrid-g5-972'
perf_6h = db.get_bot_performance(bot_name, hours=6)

print(f"DB function result for {bot_name}:")
print(f"  Result: {perf_6h}")
print(f"  Type: {type(perf_6h)}")
print(f"  win_rate: {perf_6h.get('win_rate', 'NOT FOUND')}")
print(f"  win_rate type: {type(perf_6h.get('win_rate'))}")

# Test what the server should be setting
win_rate_6h = perf_6h.get('win_rate', 0)
print(f"\nServer would set win_rate_6h to: {win_rate_6h}")
print(f"Type: {type(win_rate_6h)}")

# Test the calculation that would happen in frontend
frontend_calc = win_rate_6h * 100
print(f"\nFrontend calculation: {win_rate_6h} * 100 = {frontend_calc}")
print(f"Formatted: {frontend_calc:.1f}%")