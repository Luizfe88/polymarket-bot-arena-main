#!/usr/bin/env python3
"""
Testar diferentes endpoints da API do Polymarket
"""

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_different_endpoints():
    """Testar diferentes endpoints da API"""
    
    now = datetime.now(timezone.utc)
    
    # Diferentes endpoints para testar
    endpoints = [
        {
            "name": "Active Markets (current)",
            "url": "https://gamma-api.polymarket.com/markets",
            "params": {"limit": 10, "active": "true", "orderBy": "volume", "orderDirection": "desc"}
        },
        {
            "name": "All Markets (recent)",
            "url": "https://gamma-api.polymarket.com/markets", 
            "params": {"limit": 10, "orderBy": "createdAt", "orderDirection": "desc"}
        },
        {
            "name": "Markets by Date Range",
            "url": "https://gamma-api.polymarket.com/markets",
            "params": {
                "limit": 10,
                "endDateMin": now.isoformat(),
                "orderBy": "endDate",
                "orderDirection": "asc"
            }
        },
        {
            "name": "Featured Markets",
            "url": "https://gamma-api.polymarket.com/markets/featured",
            "params": {"limit": 10}
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for endpoint in endpoints:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing: {endpoint['name']}")
        logging.info(f"URL: {endpoint['url']}")
        logging.info(f"Params: {endpoint['params']}")
        logging.info("="*60)
        
        try:
            response = requests.get(endpoint['url'], params=endpoint['params'], headers=headers, timeout=15)
            response.raise_for_status()
            markets = response.json()
            
            logging.info(f"Found {len(markets)} markets")
            
            if markets:
                # Mostrar o primeiro mercado de cada endpoint
                market = markets[0]
                question = market.get("question", "N/A")
                end_date_str = market.get("endDate")
                volume = float(market.get("volume", 0))
                created_at = market.get("createdAt", "N/A")
                
                if end_date_str:
                    try:
                        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        time_to_resolution = end_dt - now
                        hours_to_resolution = time_to_resolution.total_seconds() / 3600
                        
                        logging.info(f"First market:")
                        logging.info(f"  Question: {question}")
                        logging.info(f"  Volume: ${volume:,.0f}")
                        logging.info(f"  Created: {created_at}")
                        logging.info(f"  End Date: {end_date_str}")
                        logging.info(f"  Hours to resolution: {hours_to_resolution:.1f}")
                        
                        # Contar mercados futuros
                        future_count = 0
                        for m in markets:
                            end_str = m.get("endDate")
                            if end_str:
                                try:
                                    end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                                    if end_dt > now:
                                        future_count += 1
                                except:
                                    pass
                        
                        logging.info(f"Future markets in this batch: {future_count}")
                        
                    except Exception as e:
                        logging.error(f"Error processing date: {e}")
                else:
                    logging.info("No end date found")
            else:
                logging.info("No markets returned")
                
        except Exception as e:
            logging.error(f"Error fetching markets: {e}")

if __name__ == "__main__":
    test_different_endpoints()