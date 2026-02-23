import requests
import json

# Test the API on the correct port
try:
    response = requests.get('http://localhost:8510/api/bots')
    data = response.json()
    
    if data and len(data) > 0:
        first_bot = data[0]
        print('First bot data:')
        print(f'Bot name: {first_bot["config"]["bot_name"]}')
        print(f'win_rate_6h: {first_bot.get("win_rate_6h", "NOT FOUND")}')
        print(f'Type of win_rate_6h: {type(first_bot.get("win_rate_6h"))}')
        
        # Check if win_rate_6h is NaN
        win_rate_6h = first_bot.get("win_rate_6h")
        if str(win_rate_6h) == 'nan' or (isinstance(win_rate_6h, float) and win_rate_6h != win_rate_6h):
            print("win_rate_6h is NaN!")
        
        print(f'\nFull first bot data structure:')
        # Print just the keys to see the structure
        print(f'Keys in first bot: {list(first_bot.keys())}')
        if 'performance_6h' in first_bot:
            print(f'Keys in performance_6h: {list(first_bot["performance_6h"].keys())}')
    else:
        print("No data returned from API")
        
except Exception as e:
    print(f"Error: {e}")