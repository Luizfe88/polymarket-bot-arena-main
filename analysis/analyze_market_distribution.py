"""
Script to analyze the distribution of market data and find qualified markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime, timedelta, timezone
from market_discovery import fetch_all_markets, calculate_spread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_markets():
    """Analyze market distribution and find potential qualified markets"""
    markets = fetch_all_markets(max_pages=3)  # Fetch fewer pages for analysis

    total_markets = len(markets)
    logging.info(f"Analyzing {total_markets} markets...")

    # Statistics
    volume_stats = []
    spread_stats = []
    time_to_resolution_stats = []
    category_stats = {}

    # Counters for different conditions
    active_markets = 0
    future_resolution = 0
    positive_volume = 0
    reasonable_spread = 0
    priority_category = 0

    now = datetime.now(timezone.utc)

    for market in markets:
        try:
            # Using Gamma Markets API field names
            volume = float(market.get('volume', 0))
            category = market.get('category', 'Unknown').lower()
            end_date_str = market.get('endDate')
            is_active = market.get('active', False)

            if not end_date_str:
                continue

            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            time_to_resolution = end_date - now
            spread = calculate_spread(market)

            # Update statistics
            volume_stats.append(volume)
            spread_stats.append(spread)
            time_to_resolution_stats.append(time_to_resolution.total_seconds() / 3600)  # hours
            category_stats[category] = category_stats.get(category, 0) + 1

            # Check conditions
            if is_active:
                active_markets += 1
            if time_to_resolution > timedelta(0):
                future_resolution += 1
            if volume > 0:
                positive_volume += 1
            if spread < 0.05:  # 5% spread
                reasonable_spread += 1

            # Check priority categories
            priority_categories = ['politics', 'crypto', 'sports', 'macro', 'tech']
            if any(cat in category for cat in priority_categories):
                priority_category += 1

            # Log potential qualified markets
            if (volume >= 10000 and
                spread <= 0.05 and
                timedelta(hours=24) <= time_to_resolution <= timedelta(days=45) and
                is_active and
                any(cat in category for cat in priority_categories)):

                logging.info(f"POTENTIAL QUALIFIED: {market.get('question')}")
                logging.info(f"  Volume: ${volume:,.0f} | Spread: {spread:.2%} | Time: {time_to_resolution} | Category: {category}")

        except Exception as e:
            continue
    
    # Print summary statistics
    logging.info("\n=== MARKET ANALYSIS SUMMARY ===")
    logging.info(f"Total markets analyzed: {total_markets}")
    logging.info(f"Active markets: {active_markets}")
    logging.info(f"Markets with future resolution: {future_resolution}")
    logging.info(f"Markets with positive volume: {positive_volume}")
    logging.info(f"Markets with reasonable spread (<5%): {reasonable_spread}")
    logging.info(f"Markets in priority categories: {priority_category}")
    
    if volume_stats:
        logging.info(f"\nVolume statistics:")
        logging.info(f"  Min: ${min(volume_stats):,.0f}")
        logging.info(f"  Max: ${max(volume_stats):,.0f}")
        logging.info(f"  Avg: ${sum(volume_stats)/len(volume_stats):,.0f}")
        
    if spread_stats:
        logging.info(f"\nSpread statistics:")
        logging.info(f"  Min: {min(spread_stats):.2%}")
        logging.info(f"  Max: {max(spread_stats):.2%}")
        logging.info(f"  Avg: {sum(spread_stats)/len(spread_stats):.2%}")
        
    if time_to_resolution_stats:
        logging.info(f"\nTime to resolution statistics (hours):")
        logging.info(f"  Min: {min(time_to_resolution_stats):,.0f}")
        logging.info(f"  Max: {max(time_to_resolution_stats):,.0f}")
        logging.info(f"  Avg: {sum(time_to_resolution_stats)/len(time_to_resolution_stats):,.0f}")
        
    logging.info(f"\nCategory distribution:")
    for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        logging.info(f"  {category}: {count}")

if __name__ == "__main__":
    analyze_markets()