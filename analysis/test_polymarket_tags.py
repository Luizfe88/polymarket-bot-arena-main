"""
Test Polymarket /api/tags endpoint and search for current market endpoints
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_polymarket_tags():
    """Test Polymarket /api/tags endpoint"""
    
    logging.info("=== Testing Polymarket /api/tags endpoint ===")
    
    try:
        url = "https://polymarket.com/api/tags"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        tags = response.json()
        logging.info(f"Got {len(tags)} tags from Polymarket API")
        
        # Show first few tags
        for i, tag in enumerate(tags[:5]):
            logging.info(f"Tag {i+1}: {tag.get('name', 'Unknown')} - {tag.get('slug', 'No slug')}")
        
    except Exception as e:
        logging.error(f"Tags API failed: {e}")
    
    # Test different Gamma API parameters for current markets
    logging.info("\n=== Testing Gamma API with current date filter ===")
    try:
        # Get current date and future date
        now = datetime.now(timezone.utc)
        future_date = (now + timedelta(days=30)).isoformat()
        
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'limit': 20,
            'endDateMin': now.isoformat(),  # Markets ending after now
            'endDateMax': future_date,      # Markets ending within 30 days
            'active': 'true'
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} current markets from Gamma API")
        
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
            
            # Check if this is a current market
            if end_date and active:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    time_left = end_dt - now
                    logging.info(f"  Time left: {time_left}")
                except:
                    pass
                    
    except Exception as e:
        logging.error(f"Current markets test failed: {e}")
    
    # Test with volume sorting
    logging.info("\n=== Testing Gamma API with volume sorting ===")
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'limit': 20,
            'sortBy': 'volume',  # Try different parameter names
            'order': 'desc'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        markets = response.json()
        logging.info(f"Got {len(markets)} volume-sorted markets from Gamma API")
        
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
        logging.error(f"Volume sorting test failed: {e}")

if __name__ == "__main__":
    test_polymarket_tags()