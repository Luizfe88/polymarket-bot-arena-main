"""
Test different API parameters to find active markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime, timedelta, timezone
import requests
from polymarket_client import get_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_api_parameters():
    """Test different API parameters to find active markets"""
    
    client = get_client()
    
    # Test 1: Current approach (no parameters)
    logging.info("=== Test 1: Default markets endpoint ===")
    try:
        response = client.get_markets()
        markets = response.get('data', [])
        logging.info(f"Got {len(markets)} markets")
        
        # Check first few markets
        for i, market in enumerate(markets[:5]):
            volume = market.get('volume_usd_24h', 0)
            active = market.get('active', False)
            end_date = market.get('end_date_iso', '')
            category = market.get('category', 'Unknown')
            logging.info(f"Market {i+1}: Volume=${volume}, Active={active}, End={end_date[:10] if end_date else 'None'}, Category={category}")
            
    except Exception as e:
        logging.error(f"Test 1 failed: {e}")
    
    # Test 2: Try with different parameters
    logging.info("\n=== Test 2: Testing with active=True parameter ===")
    try:
        # Try direct API call with parameters
        url = "https://clob.polymarket.com/markets"
        params = {
            'active': 'true',
            'limit': 100
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        markets = data.get('data', [])
        logging.info(f"Got {len(markets)} markets with active=true")
        
        # Check first few markets
        for i, market in enumerate(markets[:5]):
            volume = market.get('volume_usd_24h', 0)
            active = market.get('active', False)
            end_date = market.get('end_date_iso', '')
            category = market.get('category', 'Unknown')
            logging.info(f"Market {i+1}: Volume=${volume}, Active={active}, End={end_date[:10] if end_date else 'None'}, Category={category}")
            
    except Exception as e:
        logging.error(f"Test 2 failed: {e}")
    
    # Test 3: Try with recent date filter
    logging.info("\n=== Test 3: Testing with recent markets ===")
    try:
        # Calculate date 30 days ago
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        params = {
            'min_end_date': thirty_days_ago,
            'limit': 100
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        markets = data.get('data', [])
        logging.info(f"Got {len(markets)} markets with min_end_date filter")
        
        # Check first few markets
        for i, market in enumerate(markets[:5]):
            volume = market.get('volume_usd_24h', 0)
            active = market.get('active', False)
            end_date = market.get('end_date_iso', '')
            category = market.get('category', 'Unknown')
            logging.info(f"Market {i+1}: Volume=${volume}, Active={active}, End={end_date[:10] if end_date else 'None'}, Category={category}")
            
    except Exception as e:
        logging.error(f"Test 3 failed: {e}")

if __name__ == "__main__":
    test_api_parameters()