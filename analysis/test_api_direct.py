import requests
import json

# Test the API
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
        print(json.dumps(first_bot, indent=2))
    else:
        print("No data returned from API")
except requests.exceptions.RequestException as e:
    print(f"Error connecting to API: {e}")
        