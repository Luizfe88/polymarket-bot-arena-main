import os
import logging
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

class MarketDiscovery:
    """
    Motor de descoberta de mercados consolidado (v3.0+)
    Suporta feature flags para diferentes tipos de ativos.
    """

    def __init__(self, 
                 enable_crypto: bool = True,
                 enable_finance: bool = True,
                 enable_politics: bool = False,
                 enable_sports: bool = False,
                 min_volume: float = None,
                 min_liquidity: float = None,
                 max_spread: float = None):
        
        self.enable_crypto = enable_crypto
        self.enable_finance = enable_finance
        self.enable_politics = enable_politics
        self.enable_sports = enable_sports
        
        # Load defaults from config if not provided
        self.min_volume = min_volume if min_volume is not None else getattr(config, "MIN_MARKET_VOLUME", 50000)
        self.min_liquidity = min_liquidity if min_liquidity is not None else getattr(config, "MIN_LIQUIDITY", 0.0)
        self.max_spread = max_spread if max_spread is not None else getattr(config, "MAX_MARKET_SPREAD", 0.05)

        # Keywords for classification
        self.KEYWORDS = {
            "crypto": ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto", "token", "nft", "defi"],
            "finance": ["fed", "inflation", "interest rate", "cpi", "gdp", "recession", "treasury", "s&p 500", "nasdaq", "dow jones", "stock", "ipo", "oil", "gold", "silver", "eur", "usd", "yield"],
            "politics": ["trump", "biden", "harris", "election", "poll", "vote", "senate", "house", "president", "democrat", "republican"],
            "sports": ["nba", "nfl", "nhl", "mlb", "soccer", "cup", "game", "league", "tournament", "champion"]
        }
        
        # Blocklist for safety (ignored if category explicitly enabled)
        self.BLOCK_KEYWORDS = [
            'actor', 'oscar', 'academy award', 'best picture', # Pop culture
        ]

    def fetch_active_markets(self, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Busca mercados ativos da Gamma API"""
        all_markets = []
        page = 0

        try:
            logger.info("Fetching active markets from Gamma Markets API...")
            now = datetime.now(timezone.utc)
            start_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            future_date = (now + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

            while page < max_pages:
                url = "https://gamma-api.polymarket.com/markets"
                params = {
                    "limit": 100,
                    "offset": page * 100,
                    "endDateMin": start_date,
                    "endDateMax": future_date,
                    "active": "true",
                    "closed": "false",
                    "archived": "false",
                    "orderBy": "liquidity",
                    "orderDirection": "desc"
                }
                
                headers = {
                    "User-Agent": "PolymarketBotArena/3.0"
                }

                response = requests.get(url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                if not data:
                    break
                    
                all_markets.extend(data)
                
                if len(data) < 100:
                    break
                    
                page += 1
                
            logger.info(f"Successfully fetched {len(all_markets)} raw markets.")
            return all_markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    def calculate_spread(self, market: Dict[str, Any]) -> float:
        try:
            best_bid = float(market.get("bestBid", 0))
            best_ask = float(market.get("bestAsk", 0))
            if best_bid > 0 and best_ask > 0:
                return (best_ask - best_bid) / best_ask
            return 1.0
        except:
            return 1.0

    def classify_market(self, market: Dict[str, Any]) -> str:
        """Classifica o mercado baseado em palavras-chave"""
        question = (market.get("question") or "").lower()
        category = (market.get("category") or "").lower()
        
        # Check explicit category first if reliable, otherwise use keywords
        
        # Check keywords
        for cat, keywords in self.KEYWORDS.items():
            if any(k in question for k in keywords):
                return cat
            if any(k in category for k in keywords):
                return cat
                
        return "unknown"

    def filter_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        qualified = []
        
        logger.info("Filtering markets with criteria:")
        logger.info(f"  - Crypto: {self.enable_crypto}")
        logger.info(f"  - Finance: {self.enable_finance}")
        logger.info(f"  - Politics: {self.enable_politics}")
        logger.info(f"  - Sports: {self.enable_sports}")
        logger.info(f"  - Min Vol: ${self.min_volume:,.0f}, Min Liq: ${self.min_liquidity:,.0f}, Max Spread: {self.max_spread:.2%}")

        for market in markets:
            try:
                # Basic metrics
                volume = float(market.get("volume", 0))
                liquidity = float(market.get("liquidity") or market.get("liquidityNum") or market.get("liquidityClob") or 0)
                spread = self.calculate_spread(market)
                question = (market.get("question") or "").lower()
                
                # Check metrics
                if volume < self.min_volume: continue
                if liquidity < self.min_liquidity: continue
                if spread > self.max_spread: continue
                
                # Check global blocklist
                if any(k in question for k in self.BLOCK_KEYWORDS):
                    continue
                
                # Classification and Category Filtering
                category = self.classify_market(market)
                
                is_allowed = False
                if category == "crypto" and self.enable_crypto: is_allowed = True
                elif category == "finance" and self.enable_finance: is_allowed = True
                elif category == "politics" and self.enable_politics: is_allowed = True
                elif category == "sports" and self.enable_sports: is_allowed = True
                
                if is_allowed:
                    market["mapped_category"] = category
                    qualified.append(market)
                    
            except Exception as e:
                continue
                
        # Sort by liquidity
        qualified.sort(key=lambda x: float(x.get("liquidity", 0) or 0), reverse=True)
        return qualified

    def run(self) -> List[Dict[str, Any]]:
        raw_markets = self.fetch_active_markets()
        qualified = self.filter_markets(raw_markets)
        logger.info(f"Found {len(qualified)} qualified markets.")
        return qualified

def save_markets(markets: List[Dict[str, Any]], filename: str = "qualified_markets.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(markets, f, indent=2)
        logger.info(f"Saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save: {e}")
