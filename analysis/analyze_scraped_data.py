"""
Analyze scraped market data to understand filtering issues
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_scraped_data():
    """Analyze the scraped market data to understand why no markets qualify"""
    
    try:
        with open('current_markets_scraped.json', 'r') as f:
            markets = json.load(f)
    except FileNotFoundError:
        logging.error("Scraped markets file not found")
        return
    
    logging.info(f"=== Analyzing {len(markets)} scraped markets ===")
    
    # Volume analysis
    volumes = [m.get('volume', 0) for m in markets]
    logging.info(f"Volume range: ${min(volumes):,.2f} - ${max(volumes):,.2f}")
    logging.info(f"Average volume: ${sum(volumes)/len(volumes):,.2f}")
    
    volume_over_10k = sum(1 for v in volumes if v >= 10000)
    volume_over_200k = sum(1 for v in volumes if v >= 200000)
    logging.info(f"Markets with volume >= $10k: {volume_over_10k}/{len(markets)} ({volume_over_10k/len(markets)*100:.1f}%)")
    logging.info(f"Markets with volume >= $200k: {volume_over_200k}/{len(markets)} ({volume_over_200k/len(markets)*100:.1f}%)")
    
    # Date analysis
    now = datetime.now(timezone.utc)
    valid_dates = 0
    placeholder_dates = 0
    expired_dates = 0
    future_dates = 0
    
    for market in markets:
        end_date_str = market.get('endDate', '')
        if not end_date_str or end_date_str == '2500-12-31':
            placeholder_dates += 1
            continue
            
        try:
            if end_date_str.endswith('Z'):
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            else:
                end_date = datetime.fromisoformat(end_date_str)
            
            if end_date < now:
                expired_dates += 1
            else:
                future_dates += 1
                valid_dates += 1
                
                # Calculate time to resolution
                time_left = end_date - now
                days_left = time_left.days
                hours_left = time_left.total_seconds() / 3600
                
                if 1 <= days_left <= 45:
                    logging.info(f"Valid market: '{market.get('question', '')[:60]}...' - {days_left} days left, ${market.get('volume', 0):,.0f} volume")
                
        except Exception as e:
            logging.warning(f"Invalid date format: {end_date_str} - {e}")
            placeholder_dates += 1
    
    logging.info(f"\nDate analysis:")
    logging.info(f"  Valid future dates: {valid_dates}")
    logging.info(f"  Placeholder dates (2500-12-31): {placeholder_dates}")
    logging.info(f"  Expired dates: {expired_dates}")
    
    # Category analysis (from question text)
    categories_found = {'politics': 0, 'crypto': 0, 'sports': 0, 'macro': 0, 'tech': 0}
    
    for market in markets:
        question = market.get('question', '').lower()
        
        if any(word in question for word in ['trump', 'biden', 'election', 'president', 'congress', 'senate', 'fed', 'interest rate', 'gdp', 'inflation']):
            categories_found['politics'] += 1
        if any(word in question for word in ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'nft', 'defi']):
            categories_found['crypto'] += 1
        if any(word in question for word in ['world cup', 'super bowl', 'nba', 'nfl', 'soccer', 'football', 'basketball', 'baseball']):
            categories_found['sports'] += 1
        if any(word in question for word in ['stock', 'market', 'economy', 'recession', 'unemployment']):
            categories_found['macro'] += 1
        if any(word in question for word in ['ai', 'google', 'apple', 'microsoft', 'tesla', 'technology', 'model']):
            categories_found['tech'] += 1
    
    logging.info(f"\nCategory analysis (keywords in questions):")
    for category, count in categories_found.items():
        logging.info(f"  {category}: {count} markets")
    
    # Sample of high-volume markets
    high_volume_markets = sorted(markets, key=lambda x: x.get('volume', 0), reverse=True)[:10]
    logging.info(f"\nTop 10 highest volume markets:")
    for i, market in enumerate(high_volume_markets, 1):
        question = market.get('question', '')
        volume = market.get('volume', 0)
        end_date = market.get('endDate', '')
        logging.info(f"  {i}. '{question[:80]}...' - ${volume:,.0f} - {end_date}")

if __name__ == "__main__":
    analyze_scraped_data()