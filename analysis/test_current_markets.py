"""
Test different Gamma API parameters for current markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_current_markets():
    """Test different approaches to get current markets"""
    
    logging.info("=== Testing different Gamma API approaches ===")
    
    # Test 1: Try with just 'active=true' without date filter
    logging.info("\nTest 1: Active markets only")
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'limit': 20,
            'active': 'true'
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} active markets")
        
        now = datetime.now(timezone.utc)
        current_markets = 0
        
        for i, market in enumerate(markets[:5]):
            volume = market.get('volume', 0)
            active = market.get('active', False)
            end_date = market.get('endDate', '')
            category = market.get('category', 'Unknown')
            question = market.get('question', 'No question')
            
            # Check if current
            is_current = False
            if end_date and active:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    time_left = end_dt - now
                    if time_left.days > 0:
                        is_current = True
                        current_markets += 1
                except:
                    pass
            
            logging.info(f"Market {i+1}: {question[:50]}...")
            logging.info(f"  Volume=${volume}, Active={active}, Current={is_current}")
            logging.info(f"  End={end_date[:10] if end_date else 'None'}, Category={category}")
            
        logging.info(f"Found {current_markets} current markets out of {len(markets)}")
        
    except Exception as e:
        logging.error(f"Test 1 failed: {e}")
    
    # Test 2: Try different parameter names
    logging.info("\nTest 2: Different parameter names")
    param_tests = [
        {'active': 'true', 'closed': 'false'},
        {'status': 'active'},
        {'state': 'open'},
        {'resolved': 'false'},
        {'settled': 'false'}
    ]
    
    for i, params in enumerate(param_tests):
        try:
            url = "https://gamma-api.polymarket.com/markets"
            params['limit'] = 5
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            markets = response.json()
            logging.info(f"Test 2.{i+1}: {params} -> Got {len(markets)} markets")
            
        except Exception as e:
            logging.error(f"Test 2.{i+1} failed: {e}")
    
    # Test 3: Try with specific date range in Unix timestamp
    logging.info("\nTest 3: Unix timestamp date filter")
    try:
        now = datetime.now(timezone.utc)
        now_timestamp = int(now.timestamp())
        future_timestamp = int((now + timedelta(days=30)).timestamp())
        
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'limit': 20,
            'endTimeMin': now_timestamp,
            'endTimeMax': future_timestamp,
            'active': 'true'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Test 3: Unix timestamp filter -> Got {len(markets)} markets")
        
    except Exception as e:
        logging.error(f"Test 3 failed: {e}")

if __name__ == "__main__":
    test_current_markets()