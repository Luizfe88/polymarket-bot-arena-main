
import json
import logging
import requests
from datetime import datetime, timedelta, timezone

from polymarket_client import get_client
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_all_markets(max_pages=5):
    """
    Fetches active markets from Polymarket using Gamma Markets API with future date filter.
    """
    all_markets = []
    page = 0
    
    try:
        logging.info("Fetching active markets from Gamma Markets API...")
        
        # Get current date and future date (45 days from now)
        now = datetime.now(timezone.utc)
        future_date = (now + timedelta(days=45)).isoformat()
        
        while page < max_pages:
            url = "https://gamma-api.polymarket.com/markets"
            params = {
                'limit': 100,
                'offset': page * 100,
                'endDateMin': now.isoformat(),  # Only markets ending after now
                'endDateMax': future_date,      # Markets ending within 45 days
                'active': 'true'                # Only active markets
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            markets_on_page = response.json()
            if not markets_on_page:
                logging.info("No more markets found. Stopping.")
                break
                
            all_markets.extend(markets_on_page)
            logging.info(f"Fetched {len(markets_on_page)} markets. Total fetched: {len(all_markets)}")
            
            # If we got fewer than 100 markets, we've reached the end
            if len(markets_on_page) < 100:
                logging.info("Reached end of available markets.")
                break
                
            page += 1
            
        logging.info(f"Successfully fetched a total of {len(all_markets)} active markets from Gamma API.")
        return all_markets
        
    except Exception as e:
        logging.error(f"Failed to fetch markets from Gamma API: {e}")
        return []

def calculate_spread(market):
    """
    Calculates the bid-ask spread percentage using Gamma Markets API fields.
    """
    try:
        # Gamma Markets API uses different field names
        best_bid = float(market.get('bestBid', 0))
        best_ask = float(market.get('bestAsk', 0))
        
        if best_bid > 0 and best_ask > 0:
            spread = (best_ask - best_bid) / best_ask
            return spread
        else:
            return 1.0  # 100% spread if no orders
    except Exception:
        return 1.0  # 100% spread if error

def filter_markets(markets):
    """
    Filters markets based on v3.0 criteria: volume, spread, resolution time, and category.
    Uses Gamma Markets API field names.
    """
    qualified_markets = []
    now = datetime.now(timezone.utc)
    
    min_volume = getattr(config, 'MIN_MARKET_VOLUME', 200000)
    max_spread = getattr(config, 'MAX_MARKET_SPREAD', 0.02)
    min_hours = getattr(config, 'MIN_TIME_TO_RESOLUTION', 24)
    max_hours = getattr(config, 'MAX_TIME_TO_RESOLUTION', 45 * 24) # Max 45 days in hours
    priority_categories = getattr(config, 'PRIORITY_CATEGORIES', [])

    logging.info(f"Filtering markets with the following criteria:")
    logging.info(f"  - Min Volume: ${min_volume:,.0f}")
    logging.info(f"  - Max Spread: {max_spread:.2%}")
    logging.info(f"  - Time to Resolution: {min_hours}h - {max_hours / 24:.0f}d")
    logging.info(f"  - Priority Categories: {priority_categories}")

    for market in markets:
        try:
            # Using Gamma Markets API field names
            volume = float(market.get('volume', 0))
            category = market.get('category', 'Unknown').lower()
            end_date_str = market.get('endDate')
            is_active = market.get('active', False)

            if not end_date_str or not is_active:
                continue

            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            time_to_resolution = end_date - now
            spread = calculate_spread(market)

            # --- DEBUG LOGS ---
            logging.debug(
                f"Market: {market.get('question')} | "
                f"Volume: {volume} (Min: {min_volume}) | "
                f"Spread: {spread:.4f} (Max: {max_spread}) | "
                f"Time Left: {time_to_resolution} (Range: {timedelta(hours=min_hours)} to {timedelta(hours=max_hours)}) | "
                f"Category: '{category}' (In: {priority_categories}) | "
                f"Active: {is_active}"
            )
            # --- END DEBUG LOGS ---

            # Applying FILTERS
            if (volume >= min_volume and
                spread <= max_spread and
                timedelta(hours=min_hours) <= time_to_resolution <= timedelta(hours=max_hours) and
                (not priority_categories or any(cat in category for cat in priority_categories))):
                
                qualified_markets.append(market)
                logging.info(f"  [QUALIFIED] {market.get('question')} (Volume: ${volume:,.0f}, Spread: {spread:.2%})")
            else:
                logging.debug(f"  [SKIPPED] Condition failed.")


        except Exception as e:
            logging.warning(f"Could not process market {market.get('id', 'N/A')}: {e}")
            continue
            
    logging.info(f"Found {len(qualified_markets)} qualified markets out of {len(markets)}.")
    return qualified_markets

def save_qualified_markets(markets, filename="qualified_markets.json"):
    """
    Saves the list of qualified markets to a JSON file.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(markets, f, indent=2)
        logging.info(f"Successfully saved {len(markets)} qualified markets to {filename}")
    except Exception as e:
        logging.error(f"Failed to save qualified markets to {filename}: {e}")

if __name__ == "__main__":
    """
    Main execution block to run the market discovery and filtering process.
    """
    logging.info("Starting Polymarket Bot Arena v3.0 - Market Discovery Engine")
    
    all_markets = fetch_all_markets()
    
    if all_markets:
        # The structure of market objects is not yet known.
        # For now, we will assume the filter function has the right field names.
        # If this fails, the next step will be to inspect the output of fetch_all_markets.
        qualified = filter_markets(all_markets)
        save_qualified_markets(qualified)
    else:
        logging.error("No markets were fetched. Cannot proceed with filtering.")
        
    logging.info("Market Discovery Engine finished.")
