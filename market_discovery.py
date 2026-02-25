#!/usr/bin/env python3
"""
Market Discovery Entry Point (Legacy Wrapper)
Delegates to discovery.market_discovery.MarketDiscovery
"""
import argparse
import logging
import time
import os
from discovery.market_discovery import MarketDiscovery, save_markets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_scan_and_save():
    """
    Wrapper for legacy compatibility with arena.py
    """
    try:
        # Default configuration from environment or hardcoded defaults matching legacy behavior
        enable_crypto = os.getenv("ENABLE_CRYPTO", "true").lower() == "true"
        enable_finance = os.getenv("ENABLE_FINANCE", "true").lower() == "true"
        enable_politics = os.getenv("ENABLE_POLITICS", "false").lower() == "true"
        enable_sports = os.getenv("ENABLE_SPORTS", "false").lower() == "true"

        discovery = MarketDiscovery(
            enable_crypto=enable_crypto,
            enable_finance=enable_finance,
            enable_politics=enable_politics,
            enable_sports=enable_sports
        )
        markets = discovery.run()
        save_markets(markets)
        return True
    except Exception as e:
        logging.error(f"Error in run_scan_and_save: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Market Discovery v3.0 (Consolidated)")
    parser.add_argument("--scan", action="store_true", help="Run single scan")
    parser.add_argument("--watch", action="store_true", help="Run in watch mode")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds")
    
    # Feature flags
    parser.add_argument("--crypto", action="store_true", default=True, help="Enable Crypto markets")
    parser.add_argument("--finance", action="store_true", default=True, help="Enable Finance/Macro markets")
    parser.add_argument("--politics", action="store_true", default=False, help="Enable Politics markets")
    parser.add_argument("--sports", action="store_true", default=False, help="Enable Sports markets")
    
    args = parser.parse_args()
    
    # Allow env var overrides
    enable_crypto = os.getenv("ENABLE_CRYPTO", str(args.crypto)).lower() == "true"
    enable_finance = os.getenv("ENABLE_FINANCE", str(args.finance)).lower() == "true"
    enable_politics = os.getenv("ENABLE_POLITICS", str(args.politics)).lower() == "true"
    enable_sports = os.getenv("ENABLE_SPORTS", str(args.sports)).lower() == "true"

    discovery = MarketDiscovery(
        enable_crypto=enable_crypto,
        enable_finance=enable_finance,
        enable_politics=enable_politics,
        enable_sports=enable_sports
    )

    if args.watch:
        while True:
            markets = discovery.run()
            save_markets(markets)
            logging.info(f"Sleeping for {args.interval}s...")
            time.sleep(args.interval)
    else:
        markets = discovery.run()
        save_markets(markets)

if __name__ == "__main__":
    main()
