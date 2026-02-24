"""
Test Polymarket website API endpoints for current markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_polymarket_website_api():
    """Test Polymarket website API endpoints"""
    
    logging.info("=== Testing Polymarket website API endpoints ===")
    
    # Test different API endpoints found in the HTML
    endpoints = [
        "https://polymarket.com/api/markets",
        "https://polymarket.com/api/markets/live",
        "https://polymarket.com/api/markets/current",
        "https://polymarket.com/api/markets/active",
        "https://polymarket.com/_next/data/markets.json"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://polymarket.com"
    }
    
    for endpoint in endpoints:
        logging.info(f"\nTesting: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            logging.info(f"Success! Got {len(data) if isinstance(data, list) else 'object'} data")
            
            if isinstance(data, list) and data:
                # Check first market
                market = data[0]
                logging.info(f"First market: {market.get('question', 'No question')[:50]}...")
                logging.info(f"End date: {market.get('endDate', 'No date')}")
                logging.info(f"Volume: {market.get('volume', 'No volume')}")
                
                # Check if current
                end_date = market.get('endDate', '')
                if end_date:
                    try:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        is_current = end_dt > now
                        logging.info(f"Is current: {is_current} (ends in {end_dt - now})")
                    except:
                        pass
                        
            elif isinstance(data, dict):
                # Check if it has markets in the object
                for key in ['markets', 'data', 'results']:
                    if key in data and isinstance(data[key], list):
                        logging.info(f"Found {len(data[key])} markets in '{key}' field")
                        if data[key]:
                            market = data[key][0]
                            logging.info(f"First market: {market.get('question', 'No question')[:50]}...")
                        break
                        
        except Exception as e:
            logging.error(f"Failed: {e}")

if __name__ == "__main__":
    test_polymarket_website_api()