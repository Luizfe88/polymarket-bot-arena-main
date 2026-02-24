"""
Test different Polymarket API endpoints for active markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_polymarket_apis():
    """Test different Polymarket API endpoints"""
    
    # Test 1: Direct Polymarket website API
    logging.info("=== Test 1: Polymarket website API ===")
    try:
        url = "https://polymarket.com/api/markets"
        params = {
            'limit': 20,
            'sort': 'volume',
            'order': 'desc'
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} markets from Polymarket website API")
        
        # Check first few markets
        for i, market in enumerate(markets[:3]):
            volume = market.get('volume', 0)
            active = market.get('active', False)
            end_date = market.get('endDate', '')
            category = market.get('category', 'Unknown')
            question = market.get('question', 'No question')
            
            logging.info(f"Market {i+1}: {question[:60]}...")
            logging.info(f"  Volume=${volume:,.0f}, Active={active}, End={end_date[:10] if end_date else 'None'}")
            logging.info(f"  Category={category}")
            
    except Exception as e:
        logging.error(f"Polymarket website API failed: {e}")
    
    # Test 2: Try the main Polymarket markets page
    logging.info("\n=== Test 2: Polymarket markets page ===")
    try:
        url = "https://polymarket.com/markets"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for market data in the HTML
        html = response.text
        if 'markets' in html.lower():
            logging.info("Found markets page with HTML content")
            # This would require HTML parsing, but let's see if we can find API calls
        else:
            logging.info("No obvious market data in HTML")
            
    except Exception as e:
        logging.error(f"Polymarket markets page failed: {e}")
    
    # Test 3: Try different Gamma API endpoints
    logging.info("\n=== Test 3: Different Gamma API endpoints ===")
    endpoints = [
        "https://gamma-api.polymarket.com/markets/live",
        "https://gamma-api.polymarket.com/markets/active",
        "https://gamma-api.polymarket.com/markets/current",
        "https://gamma-api.polymarket.com/markets/recent"
    ]
    
    for endpoint in endpoints:
        try:
            logging.info(f"Testing {endpoint}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            
            markets = response.json()
            logging.info(f"✓ Got {len(markets)} markets from {endpoint}")
            
            # Show first market if available
            if markets:
                market = markets[0]
                volume = market.get('volume', 0)
                end_date = market.get('endDate', '')
                logging.info(f"  Sample: Volume=${volume:,.0f}, End={end_date[:10] if end_date else 'None'}")
            
        except Exception as e:
            logging.error(f"✗ {endpoint} failed: {e}")

if __name__ == "__main__":
    test_polymarket_apis()