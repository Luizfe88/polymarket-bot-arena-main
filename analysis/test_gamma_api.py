"""
Test Gamma Markets API for active markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_gamma_api():
    """Test the Gamma Markets API for active markets"""
    
    logging.info("=== Testing Gamma Markets API ===")
    
    try:
        # Gamma Markets API endpoint
        url = "https://gamma-api.polymarket.com/markets"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        params = {
            'limit': 50,  # Start with fewer markets
            'active': 'true'  # Try to get only active markets
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} markets from Gamma API")
        
        # Check first few markets
        for i, market in enumerate(markets[:10]):
            volume = market.get('volume', 0)
            active = market.get('active', False)
            end_date = market.get('endDate', '')
            category = market.get('category', 'Unknown')
            question = market.get('question', 'No question')
            
            logging.info(f"Market {i+1}: {question[:50]}...")
            logging.info(f"  Volume=${volume}, Active={active}, End={end_date[:10] if end_date else 'None'}, Category={category}")
            
            # Check if this is a current market
            if end_date and active and volume > 0:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    time_left = end_dt - datetime.now(timezone.utc)
                    logging.info(f"  Time left: {time_left}")
                except:
                    pass
            
    except Exception as e:
        logging.error(f"Gamma API test failed: {e}")
        
    # Also test without active filter
    logging.info("\n=== Testing Gamma Markets API without active filter ===")
    try:
        params = {'limit': 20}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} markets (no active filter)")
        
        # Count active vs inactive
        active_count = sum(1 for m in markets if m.get('active', False))
        volume_positive = sum(1 for m in markets if m.get('volume', 0) > 0)
        
        logging.info(f"Active markets: {active_count}/{len(markets)}")
        logging.info(f"Markets with volume > 0: {volume_positive}/{len(markets)}")
        
    except Exception as e:
        logging.error(f"Second Gamma API test failed: {e}")

if __name__ == "__main__":
    test_gamma_api()