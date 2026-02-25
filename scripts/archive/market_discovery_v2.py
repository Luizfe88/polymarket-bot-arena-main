"""
Market Discovery Engine for Polymarket v3.0
Uses scraped data from Polymarket website for current markets
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Add the parent directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MIN_MARKET_VOLUME, MAX_MARKET_SPREAD, MIN_TIME_TO_RESOLUTION,
    MAX_TIME_TO_RESOLUTION, PRIORITY_CATEGORIES
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_scraped_markets(file_path: str = 'analysis/current_markets_scraped.json') -> List[Dict[str, Any]]:
    """
    Loads scraped market data from file.
    """
    try:
        with open(file_path, 'r') as f:
            markets = json.load(f)
            logging.info(f"Loaded {len(markets)} markets from scraped data")
            return markets
    except FileNotFoundError:
        logging.error(f"Scraped markets file not found: {file_path}")
        return []
    except Exception as e:
        logging.error(f"Failed to load scraped markets: {e}")
        return []

def calculate_spread(market: Dict[str, Any]) -> float:
    """
    Calculates the bid-ask spread percentage.
    For scraped data, we'll estimate based on typical spreads.
    """
    # Since we don't have order book data from scraping, 
    # we'll use a default spread based on volume
    volume = float(market.get('volume', 0))
    
    if volume > 100000000:  # >$100M
        return 0.01  # 1% spread for high volume
    elif volume > 10000000:  # >$10M
        return 0.02  # 2% spread for medium-high volume
    elif volume > 1000000:  # >$1M
        return 0.03  # 3% spread for medium volume
    elif volume > 100000:  # >$100k
        return 0.05  # 5% spread for low-medium volume
    else:
        return 0.10  # 10% spread for low volume

def parse_end_date(end_date_str: str, question: str = '') -> datetime:
    """
    Parses end date string to datetime object.
    For placeholder dates, estimates based on question content.
    """
    try:
        if end_date_str and end_date_str != '2500-12-31':
            # Handle different date formats
            if 'T' in end_date_str:
                return datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(end_date_str + 'T00:00:00+00:00')
        else:
            # For markets with placeholder end dates, estimate based on question
            question_lower = question.lower()
            
            # Sports events (usually within months)
            if any(word in question_lower for word in ['game', 'match', 'tournament', 'championship', 'world cup', 'super bowl', 'nba', 'nfl', 'masters']):
                return datetime.now(timezone.utc) + timedelta(days=30)
            
            # Politics (elections usually have known dates)
            if '2026' in question_lower:
                return datetime(2026, 12, 31, tzinfo=timezone.utc)
            elif '2027' in question_lower:
                return datetime(2027, 12, 31, tzinfo=timezone.utc)
            elif '2028' in question_lower:
                return datetime(2028, 12, 31, tzinfo=timezone.utc)
            
            # Default for other cases
            return datetime.now(timezone.utc) + timedelta(days=90)  # 3 months default
    except Exception as e:
        logging.warning(f"Failed to parse date '{end_date_str}': {e}")
        return datetime.now(timezone.utc) + timedelta(days=90)

def filter_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters markets based on v3.0 quality criteria.
    """
    qualified_markets = []
    now = datetime.now(timezone.utc)
    
    logging.info(f"Filtering markets with the following criteria: ")
    logging.info(f"   - Min Volume: ${MIN_MARKET_VOLUME:,}")
    logging.info(f"   - Max Spread: {MAX_MARKET_SPREAD:.1%}")
    logging.info(f"   - Time to Resolution: {MIN_TIME_TO_RESOLUTION}h - {MAX_TIME_TO_RESOLUTION/24:.0f}d")
    logging.info(f"   - Priority Categories: {PRIORITY_CATEGORIES}")
    
    for market in markets:
        try:
            # Extract market data
            question = market.get('question', '')
            volume = float(market.get('volume', 0))
            end_date_str = market.get('endDate', '')
            category = market.get('category', 'Unknown').lower()
            
            # Skip if missing essential data
            if not question or volume <= 0:
                continue
            
            # Calculate spread
            spread = calculate_spread(market)
            
            # Parse end date
            end_date = parse_end_date(end_date_str, question)
            time_to_resolution = end_date - now
            hours_to_resolution = time_to_resolution.total_seconds() / 3600
            
            # Apply filters
            volume_qualified = volume >= MIN_MARKET_VOLUME
            spread_qualified = spread <= MAX_MARKET_SPREAD
            time_qualified = (MIN_TIME_TO_RESOLUTION <= hours_to_resolution <= MAX_TIME_TO_RESOLUTION)
            
            # Check category (improved detection)
            question_lower = question.lower()
            category_qualified = any(cat in category for cat in PRIORITY_CATEGORIES) or \
                               any(cat in question_lower for cat in PRIORITY_CATEGORIES) or \
                               any(word in question_lower for word in ['trump', 'biden', 'election', 'president', 'congress', 'senate', 'fed', 'interest rate', 'gdp', 'inflation']) or \
                               any(word in question_lower for word in ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'nft', 'defi']) or \
                               any(word in question_lower for word in ['world cup', 'super bowl', 'nba', 'nfl', 'soccer', 'football', 'basketball', 'baseball', 'masters', 'tournament']) or \
                               any(word in question_lower for word in ['stock', 'market', 'economy', 'recession', 'unemployment']) or \
                               any(word in question_lower for word in ['ai', 'google', 'apple', 'microsoft', 'tesla', 'technology', 'model', 'software'])
            
            # Overall qualification
            qualified = volume_qualified and spread_qualified and time_qualified and category_qualified
            
            if qualified:
                qualified_market = {
                    'question': question,
                    'volume': volume,
                    'spread': spread,
                    'endDate': end_date.isoformat(),
                    'timeToResolutionHours': hours_to_resolution,
                    'category': category,
                    'source': 'scraped',
                    'timestamp': now.isoformat()
                }
                qualified_markets.append(qualified_market)
                
                logging.info(f"QUALIFIED: {question[:60]}...")
                logging.info(f"  Volume: ${volume:,.0f} | Spread: {spread:.2%} | Time: {hours_to_resolution:.0f}h | Category: {category}")
            
        except Exception as e:
            logging.warning(f"Failed to process market: {e}")
            continue
    
    return qualified_markets

def save_qualified_markets(markets: List[Dict[str, Any]], filename: str = 'qualified_markets.json'):
    """
    Saves qualified markets to JSON file.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(markets, f, indent=2)
        logging.info(f"Successfully saved {len(markets)} qualified markets to {filename}")
    except Exception as e:
        logging.error(f"Failed to save qualified markets: {e}")

def main():
    """
    Main function to discover and filter markets.
    """
    logging.info("Starting Polymarket Bot Arena v3.0 - Market Discovery Engine")
    
    # Load scraped markets
    markets = load_scraped_markets()
    if not markets:
        logging.error("No markets loaded. Exiting.")
        return
    
    # Filter markets
    qualified_markets = filter_markets(markets)
    
    logging.info(f"Found {len(qualified_markets)} qualified markets out of {len(markets)} total markets")
    
    # Save results
    save_qualified_markets(qualified_markets)
    
    logging.info("Market Discovery Engine finished.")

if __name__ == "__main__":
    main()