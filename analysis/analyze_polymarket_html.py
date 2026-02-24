"""
Analyze Polymarket website to find current markets data source
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
import re
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_polymarket_html():
    """Analyze Polymarket website HTML to find market data sources"""
    
    logging.info("=== Analyzing Polymarket website HTML ===")
    
    try:
        url = "https://polymarket.com"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        html = response.text
        logging.info(f"Downloaded {len(html)} characters of HTML")
        
        # Look for API endpoints in the HTML
        api_patterns = [
            r'api\.polymarket\.com[^"\']*',
            r'gamma-api\.polymarket\.com[^"\']*',
            r'clob\.polymarket\.com[^"\']*',
            r'"/api/[^"\']*"',
            r'"/markets[^"\']*"',
            r'"https://[^"]*polymarket[^"]*"'
        ]
        
        logging.info("Searching for API endpoints in HTML...")
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html)
            if matches:
                logging.info(f"Found {len(matches)} matches for pattern: {pattern}")
                for match in matches[:5]:  # Show first 5 matches
                    logging.info(f"  {match}")
        
        # Look for JavaScript objects with market data
        logging.info("\nSearching for market data in JavaScript...")
        
        # Look for JSON-like structures
        json_patterns = [
            r'\{[^}]*"markets"[^}]*\}',
            r'\{[^}]*"volume"[^}]*\}',
            r'\{[^}]*"question"[^}]*\}',
            r'window\.__INITIAL_STATE__\s*=\s*\{[^}]*\}'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                logging.info(f"Found {len(matches)} potential JSON structures")
                for match in matches[:2]:  # Show first 2 matches
                    if len(match) < 500:  # Only show small matches
                        logging.info(f"  {match[:200]}...")
        
        # Look for specific market data
        logging.info("\nSearching for current market data...")
        
        # Look for current year in dates
        current_year = str(datetime.now().year)
        year_matches = re.findall(rf'{current_year}[^"\']*', html)
        if year_matches:
            logging.info(f"Found {len(year_matches)} references to current year")
            for match in year_matches[:3]:
                logging.info(f"  {match}")
        
        # Look for recent months
        recent_months = ['January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
        
        for month in recent_months[:3]:  # Check first 3 months
            month_matches = re.findall(rf'{month}[^"\']*', html, re.IGNORECASE)
            if month_matches:
                logging.info(f"Found {len(month_matches)} references to {month}")
        
    except Exception as e:
        logging.error(f"Failed to analyze HTML: {e}")

if __name__ == "__main__":
    analyze_polymarket_html()