
import json
import logging
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_all_markets(max_pages=8):
    all_markets = []
    page = 0

    try:
        logging.info("Fetching active markets from Gamma Markets API...")

        now = datetime.now(timezone.utc)
        future_date = (now + timedelta(days=45)).isoformat()

        while page < max_pages:
            url = "https://gamma-api.polymarket.com/markets"
            params = {
                "limit": 100,
                "offset": page * 100,
                "endDateMin": now.isoformat(),
                "endDateMax": future_date,
                "active": "true",
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
    try:
        best_bid = float(market.get("bestBid", 0))
        best_ask = float(market.get("bestAsk", 0))
        if best_bid > 0 and best_ask > 0:
            return (best_ask - best_bid) / best_ask
        return 1.0
    except Exception:
        return 1.0


def _is_rejected_short_crypto(market, now):
    q = (market.get("question") or "").lower()
    assets = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol"]
    short_kw = ["up or down", "up/down", "5 min", "5-min", "5min"]
    has_asset = any(a in q for a in assets)
    has_short = any(k in q for k in short_kw)
    end_date_str = market.get("endDate")
    if not end_date_str:
        return False
    try:
        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    except Exception:
        return False
    tte_seconds = max(0, int((end_dt - now).total_seconds()))
    return has_asset and has_short and tte_seconds <= 3600

def filter_markets(markets):
    qualified_markets = []
    now = datetime.now(timezone.utc)

    min_volume = getattr(config, "MIN_MARKET_VOLUME", 150000)
    max_spread = getattr(config, "MAX_MARKET_SPREAD", 0.025)
    min_hours = getattr(config, "MIN_TIME_TO_RESOLUTION", 6)
    max_hours = getattr(config, "MAX_TIME_TO_RESOLUTION", 45 * 24)
    priority_categories = getattr(config, "PRIORITY_CATEGORIES", ["politics", "crypto", "macro", "sports", "tech"])

    logging.info("Filtering markets with the following criteria:")
    logging.info(f"  - Min Volume: ${min_volume:,.0f}")
    logging.info(f"  - Max Spread: {max_spread:.2%}")
    logging.info(f"  - Time to Resolution: {min_hours}h - {int(max_hours / 24)}d")
    logging.info(f"  - Priority Categories: {priority_categories}")

    for market in markets:
        try:
            volume = float(market.get("volume", 0))
            category = (market.get("category") or "unknown").lower()
            end_date_str = market.get("endDate")
            is_active = bool(market.get("active", False))

            if not end_date_str or not is_active:
                continue

            if _is_rejected_short_crypto(market, now):
                logging.debug("  [REJECTED] short-window crypto up/down")
                continue

            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            time_to_resolution = end_date - now
            spread = calculate_spread(market)

            logging.debug(
                f"Market: {market.get('question')} | Volume: {volume} | Spread: {spread:.4f} | "
                f"TTE: {time_to_resolution} | Category: {category} | Active: {is_active}"
            )

            if (
                volume >= min_volume
                and spread <= max_spread
                and timedelta(hours=min_hours) <= time_to_resolution <= timedelta(hours=max_hours)
                and (not priority_categories or any(cat in category for cat in priority_categories))
            ):
                qualified_markets.append(market)
                logging.info(f"  [QUALIFIED] {market.get('question')} (Vol ${volume:,.0f}, Spread {spread:.2%})")

        except Exception as e:
            logging.warning(f"Could not process market {market.get('id', 'N/A')}: {e}")
            continue

    logging.info(f"Found {len(qualified_markets)} qualified markets out of {len(markets)}.")
    return qualified_markets

def save_qualified_markets(markets, filename="qualified_markets.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(markets, f, indent=2)
        logging.info(f"Successfully saved {len(markets)} qualified markets to {filename}")
    except Exception as e:
        logging.error(f"Failed to save qualified markets to {filename}: {e}")


def run_scan_and_save():
    all_markets = fetch_all_markets()
    if not all_markets:
        logging.error("No markets were fetched. Cannot proceed with filtering.")
        return False
    qualified = filter_markets(all_markets)
    save_qualified_markets(qualified)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Discovery v3.0")
    parser.add_argument("--scan", action="store_true", help="Executa uma varredura única e salva mercados qualificados")
    parser.add_argument("--watch", action="store_true", help="Executa automaticamente a cada 60 minutos")
    parser.add_argument("--interval", type=int, default=3600, help="Intervalo em segundos para modo watch")
    args = parser.parse_args()

    logging.info("Starting Polymarket Bot Arena v3.0 - Market Discovery Engine")

    if args.watch:
        while True:
            ok = run_scan_and_save()
            if not ok:
                logging.info("Scan failed or no markets fetched.")
            logging.info(f"Sleeping for {args.interval} seconds before next scan...")
            time.sleep(args.interval)
    else:
        run_scan_and_save()
        logging.info("Market Discovery Engine finished.")
