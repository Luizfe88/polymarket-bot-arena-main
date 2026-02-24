"""
Advanced scraping to extract complete current market data from Polymarket
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_current_markets():
    """Scrape current market data from Polymarket with better extraction"""
    
    logging.info("=== Advanced scraping for current markets ===")
    
    try:
        url = "https://polymarket.com"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for large JSON objects in script tags (likely Next.js data)
        script_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
        large_json_pattern = r'({[^{}]*"markets"[^{}]*})'
        
        markets_data = []
        
        # Search for JSON data in scripts
        script_matches = re.findall(script_pattern, response.text, re.DOTALL)
        logging.info(f"Found {len(script_matches)} potential initial state objects")
        
        for match in script_matches:
            try:
                # Try to parse as JSON
                data = json.loads(match)
                logging.info(f"Parsed initial state with keys: {list(data.keys())}")
                
                # Look for markets in the data
                if 'markets' in data:
                    markets = data['markets']
                    if isinstance(markets, list):
                        markets_data.extend(markets)
                        logging.info(f"Found {len(markets)} markets in initial state")
                
                # Look for nested market data
                for key, value in data.items():
                    if isinstance(value, dict) and 'markets' in value:
                        markets = value['markets']
                        if isinstance(markets, list):
                            markets_data.extend(markets)
                            logging.info(f"Found {len(markets)} markets in {key}")
                            
            except json.JSONDecodeError:
                continue
        
        # Also search for standalone market objects
        market_objects = re.findall(r'"question":\s*"([^"]*)".*?"volume":\s*([\d.]+).*?"endDate":\s*"([^"]*)"', response.text, re.DOTALL)
        logging.info(f"Found {len(market_objects)} market objects in HTML")
        
        for question, volume, end_date in market_objects:
            market_data = {
                'question': question,
                'volume': float(volume),
                'endDate': end_date,
                'source': 'scraped_html'
            }
            markets_data.append(market_data)
        
        # Look for market links and extract IDs
        market_links = re.findall(r'href="/market/([^"]*)"', response.text)
        logging.info(f"Found {len(market_links)} market links")
        
        # Remove duplicates
        unique_markets = []
        seen_questions = set()
        
        for market in markets_data:
            question = market.get('question', '')
            if question and question not in seen_questions:
                seen_questions.add(question)
                unique_markets.append(market)
        
        logging.info(f"Total unique markets found: {len(unique_markets)}")
        
        # Analyze the markets
        current_markets = []
        now = datetime.now(timezone.utc)
        
        for market in unique_markets:
            question = market.get('question', '')
            volume = market.get('volume', 0)
            end_date = market.get('endDate', '')
            
            # Check if it's a current market
            is_current = False
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    time_left = end_dt - now
                    if time_left.days > 0 and time_left.days < 365:  # Future but within a year
                        is_current = True
                        current_markets.append(market)
                except:
                    # If no end date, check if it mentions future dates
                    if any(year in question for year in ['2026', '2027', '2028']):
                        is_current = True
                        current_markets.append(market)
            
            logging.info(f"Market: {question[:60]}...")
            logging.info(f"  Volume: ${volume:,.0f}, End: {end_date[:10] if end_date else 'None'}, Current: {is_current}")
        
        logging.info(f"\nFound {len(current_markets)} current markets")
        
        # Save current markets
        if current_markets:
            with open('current_markets_scraped.json', 'w') as f:
                json.dump(current_markets, f, indent=2)
            logging.info(f"Saved {len(current_markets)} current markets to current_markets_scraped.json")
            
            # Show summary
            total_volume = sum(m.get('volume', 0) for m in current_markets)
            avg_volume = total_volume / len(current_markets) if current_markets else 0
            
            logging.info(f"\n=== Current Markets Summary ===")
            logging.info(f"Total markets: {len(current_markets)}")
            logging.info(f"Total volume: ${total_volume:,.0f}")
            logging.info(f"Average volume: ${avg_volume:,.0f}")
            
            # Show top markets by volume
            top_markets = sorted(current_markets, key=lambda x: x.get('volume', 0), reverse=True)[:5]
            logging.info(f"\nTop 5 markets by volume:")
            for i, market in enumerate(top_markets, 1):
                logging.info(f"{i}. {market['question'][:60]}... (${market.get('volume', 0):,.0f})")
        
        return current_markets
        
    except Exception as e:
        logging.error(f"Failed to scrape markets: {e}")
        return []

if __name__ == "__main__":
    markets = scrape_current_markets()