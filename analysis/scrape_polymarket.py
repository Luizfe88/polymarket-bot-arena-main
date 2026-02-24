"""
Scrape Polymarket website to extract current market data from HTML
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

def scrape_polymarket_markets():
    """Scrape current market data from Polymarket website"""
    
    logging.info("=== Scraping Polymarket website for current markets ===")
    
    try:
        url = "https://polymarket.com"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logging.info(f"Downloaded and parsed HTML")
        
        # Look for market data in script tags
        script_tags = soup.find_all('script')
        logging.info(f"Found {len(script_tags)} script tags")
        
        markets_found = []
        
        for i, script in enumerate(script_tags):
            if script.string and ('market' in script.string.lower() or 'question' in script.string.lower()):
                logging.info(f"Script {i+1}: Found potential market data")
                
                # Look for JSON-like structures
                json_patterns = [
                    r'\{[^{}]*"question"[^{}]*\}',
                    r'\{[^{}]*"markets"[^{}]*\}',
                    r'window\.__INITIAL_STATE__\s*=\s*\{[^}]*\}',
                    r'"markets":\s*\[[^\]]*\]',
                    r'"market":\s*\{[^}]*\}'
                ]
                
                for pattern in json_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE | re.DOTALL)
                    if matches:
                        logging.info(f"  Found {len(matches)} potential JSON structures")
                        for match in matches[:2]:
                            try:
                                # Try to extract market data
                                if 'question' in match:
                                    # Look for specific market data
                                    question_match = re.search(r'"question":\s*"([^"]*)"', match)
                                    volume_match = re.search(r'"volume":\s*([\d.]+)', match)
                                    end_date_match = re.search(r'"endDate":\s*"([^"]*)"', match)
                                    
                                    if question_match:
                                        market_data = {
                                            'question': question_match.group(1),
                                            'volume': float(volume_match.group(1)) if volume_match else 0,
                                            'endDate': end_date_match.group(1) if end_date_match else '',
                                            'source': 'scraped'
                                        }
                                        markets_found.append(market_data)
                                        logging.info(f"    Found market: {market_data['question'][:50]}...")
                                        
                            except Exception as e:
                                continue
        
        # Also look for market cards in the HTML
        logging.info("\nLooking for market cards in HTML...")
        
        # Look for elements that might contain market data
        market_selectors = [
            'a[href*="market"]',
            '[data-testid*="market"]',
            '.market-card',
            '.market-item',
            '[class*="market"]'
        ]
        
        for selector in market_selectors:
            elements = soup.select(selector)
            if elements:
                logging.info(f"Found {len(elements)} elements with selector: {selector}")
                for elem in elements[:3]:  # Check first 3
                    text = elem.get_text(strip=True)
                    if text and len(text) > 10:  # Reasonable text length
                        logging.info(f"  Text: {text[:100]}...")
                        
                        # Look for href to get market ID
                        href = elem.get('href', '')
                        if href and 'market' in href:
                            logging.info(f"  Link: {href}")
        
        logging.info(f"\nTotal markets found: {len(markets_found)}")
        
        # Save scraped data
        if markets_found:
            with open('scraped_markets.json', 'w') as f:
                json.dump(markets_found, f, indent=2)
            logging.info(f"Saved {len(markets_found)} scraped markets to scraped_markets.json")
        
        return markets_found
        
    except Exception as e:
        logging.error(f"Failed to scrape markets: {e}")
        return []

if __name__ == "__main__":
    markets = scrape_polymarket_markets()
    
    if markets:
        logging.info("\n=== Sample Scraped Markets ===")
        for market in markets[:3]:
            logging.info(f"Question: {market['question']}")
            logging.info(f"Volume: ${market['volume']:,.0f}")
            logging.info(f"End Date: {market['endDate']}")
            logging.info("---")