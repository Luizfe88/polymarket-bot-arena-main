import requests
import json

# Test the API
try:
    response = requests.get('http://localhost:8510/api/bots')
    data = response.json()
    
    # Check the first bot's data
    if data:
        first_bot = data[0]
        print('First bot data:')
        print(f'Bot name: {first_bot["config"]["bot_name"]}')
        print(f'Performance 6h: {first_bot.get("performance_6h")}')
        print(f'Win rate 6h: {first_bot.get("win_rate_6h", "NOT FOUND")}')
        print()
        
        # Check if win_rate exists in performance_6h
        if 'performance_6h' in first_bot:
            perf_6h = first_bot['performance_6h']
            print(f'win_rate in performance_6h: {perf_6h.get("win_rate", "NOT FOUND")}')
            print(f'Type of win_rate: {type(perf_6h.get("win_rate"))}')
    else:
        print("No data returned from API")
except requests.exceptions.RequestException as e:
    print(f"Error connecting to API: {e}")
        