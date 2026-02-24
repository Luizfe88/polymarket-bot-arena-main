"""
Test Gamma Markets API with future markets filter
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_future_markets():
    """Test Gamma Markets API with future markets"""
    
    logging.info("=== Testing Gamma Markets API for future markets ===")
    
    try:
        # Calculate future date (tomorrow)
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'limit': 50,
            'min_end_date': tomorrow  # Only markets ending after tomorrow
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} future markets")
        
        # Check first few markets
        for i, market in enumerate(markets[:5]):
            volume = market.get('volume', 0)
            active = market.get('active', False)
            end_date = market.get('endDate', '')
            category = market.get('category', 'Unknown')
            question = market.get('question', 'No question')
            best_bid = market.get('bestBid', 0)
            best_ask = market.get('bestAsk', 0)
            
            spread = 1.0
            if best_bid and best_ask:
                spread = (best_ask - best_bid) / best_ask
            
            logging.info(f"Market {i+1}: {question[:60]}...")
            logging.info(f"  Volume=${volume:,.0f}, Active={active}, End={end_date[:10] if end_date else 'None'}")
            logging.info(f"  Category={category}, Bid={best_bid}, Ask={best_ask}, Spread={spread:.2%}")
            
            # Check if this is a current market
            if end_date and active:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    time_left = end_dt - datetime.now(timezone.utc)
                    logging.info(f"  Time left: {time_left}")
                except:
                    pass
                    
    except Exception as e:
        logging.error(f"Future markets test failed: {e}")
        
    # Test with different parameters
    logging.info("\n=== Testing with different parameters ===")
    try:
        # Try with active=true and sort by volume
        params = {
            'limit': 20,
            'active': 'true',
            'sort': 'volume',
            'order': 'desc'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} active markets sorted by volume")
        
        # Check first few markets
        for i, market in enumerate(markets[:3]):
            volume = market.get('volume', 0)
            active = market.get('active', False)
            end_date = market.get('endDate', '')
            category = market.get('category', 'Unknown')
            question = market.get('question', 'No question')
            best_bid = market.get('bestBid', 0)
            best_ask = market.get('bestAsk', 0)
            
            spread = 1.0
            if best_bid and best_ask:
                spread = (best_ask - best_bid) / best_ask
            
            logging.info(f"Market {i+1}: {question[:60]}...")
            logging.info(f"  Volume=${volume:,.0f}, Active={active}, End={end_date[:10] if end_date else 'None'}")
            logging.info(f"  Category={category}, Bid={best_bid}, Ask={best_ask}, Spread={spread:.2%}")
            
    except Exception as e:
        logging.error(f"Alternative test failed: {e}")

if __name__ == "__main__":
    test_future_markets()