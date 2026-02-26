import os
import logging
import json
import time
import requests
import base64
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sys
import os

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            "crypto": [
                "bitcoin", "btc", "ethereum", "eth", "solana", "sol", 
                "crypto", "token", "nft", "defi", "xrp", "ripple", 
                "bnb", "avax", "doge", "matic", "up or down", "updown"
            ],
            "finance": ["fed", "inflation", "interest rate", "cpi", "gdp", "recession", "treasury", "s&p 500", "nasdaq", "dow jones", "stock", "ipo", "oil", "gold", "silver", "eur", "usd", "yield"],
            "politics": ["trump", "biden", "harris", "election", "poll", "vote", "senate", "house", "president", "democrat", "republican"],
            "sports": ["nba", "nfl", "nhl", "mlb", "soccer", "cup", "game", "league", "tournament", "champion"]
        }
        
        # Blocklist for safety (ignored if category explicitly enabled)
        self.BLOCK_KEYWORDS = [
            "israel", "gaza", "hamas", "ukraine", "russia", "war", "death", "kill", 
            "trump", "biden", "harris", "election", "president", "senate", "house",
            "taylor swift", "kanye", "drake", "movie", "box office", "song", "album",
            "weather", "temperature", "earthquake", "hurricane"
        ]

    def fetch_active_markets(self, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Busca mercados ativos (Gamma API + CLOB API para curto prazo)"""
        all_markets = []
        page = 0

        # Targeted search for crypto keywords if enabled
        # This helps find markets that might be buried in the main list
        search_terms = []
        if self.enable_crypto:
            search_terms.extend(["bitcoin", "ethereum", "solana", "up or down", "5 min", "15 min"])
        
        try:
            logger.info("Fetching active markets from Gamma Markets API...")
            now = datetime.now(timezone.utc)
            start_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            future_date = (now + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

            # 1. Main scan (general active markets)
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
            
            # 2. CLOB API Search for "Up or Down" (Short-Term Crypto)
            if self.enable_crypto:
                logger.info("Running CLOB API search for active 'Up or Down' markets...")
                # Start scanning from offset 250,000 as per analysis (active markets are deep)
                offset = 250000 
                batch_size = 500
                found_count = 0
                
                while True:
                    try:
                        cursor = base64.b64encode(str(offset).encode()).decode()
                        url = "https://clob.polymarket.com/markets"
                        params = {"limit": batch_size, "next_cursor": cursor}
                        
                        r = requests.get(url, params=params, headers=headers, timeout=15)
                        if r.status_code != 200:
                            logger.warning(f"CLOB API returned {r.status_code}")
                            break
                            
                        data = r.json()
                        page_markets = data.get("data", [])
                        
                        if not page_markets:
                            break
                            
                        # Filter for active "Up or Down" markets
                        for m in page_markets:
                            # Only accept if strictly accepting orders (active)
                            if m.get("accepting_orders") is not True:
                                continue
                                
                            # Check "Up or Down" tag or question
                            question = (m.get("question") or "").lower()
                            tags = [t.lower() for t in m.get("tags") or []]
                            
                            if "up or down" in question or "up or down" in tags:
                                # Inject dummy metrics if missing to pass filters
                                # (CLOB markets endpoint often lacks volume/liquidity)
                                if "volume" not in m: m["volume"] = 999999
                                if "liquidity" not in m: m["liquidity"] = 999999
                                if "spread" not in m: m["spread"] = 0.0
                                
                                # Ensure ID is string
                                if "id" not in m and "condition_id" in m:
                                    m["id"] = m["condition_id"] # Fallback ID
                                
                                # Avoid duplicates
                                if not any(existing.get("id") == m.get("id") for existing in all_markets):
                                    all_markets.append(m)
                                    found_count += 1
                                    
                        offset += len(page_markets)
                        
                        # Safety break if we scanned too far or found enough
                        # But user says "active ones are deep", so we keep going until empty
                        if len(page_markets) < batch_size:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error fetching CLOB markets: {e}")
                        break
                        
                logger.info(f"  Found {found_count} active markets from CLOB.")

            logger.info(f"Successfully fetched {len(all_markets)} raw markets.")
            return all_markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    def calculate_spread(self, market: Dict[str, Any]) -> float:
        """Calcula ou obtém o spread do mercado"""
        # A API do Polymarket já retorna o campo 'spread' diretamente — use-o
        api_spread = market.get("spread")
        if api_spread is not None:
            try:
                return float(api_spread)
            except (ValueError, TypeError):
                pass

        # Fallback: calcular via bestBid/bestAsk
        try:
            best_bid = float(market.get("bestBid", 0) or 0)
            best_ask = float(market.get("bestAsk", 0) or 0)
            if best_bid > 0 and best_ask > 0:
                return (best_ask - best_bid) / best_ask
        except (ValueError, TypeError):
            pass

        return 1.0  # Spread desconhecido = máximo (mercado será rejeitado)

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

    def is_short_term_crypto(self, market: Dict[str, Any]) -> bool:
        """Identifica mercados crypto de curto prazo (5min, 15min, 1h)"""
        title = (market.get("question") or market.get("title") or "").lower()
        slug  = (market.get("slug") or "").lower()
        combined = title + " " + slug  # Checar ambos

        short_term_kws = [
            '5 min', '5 minutes', '15 min', '15 minutes',
            '5m', '15m', '1h', 'next 5', 'next 15', 'in 5',
            'up or down', 'updown', 'up-or-down'
        ]
        crypto_kws = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol',
            'xrp', 'ripple', 'bnb', 'avax', 'doge', 'matic', 'crypto'
        ]

        has_short_term = any(kw in combined for kw in short_term_kws)
        has_crypto     = any(c  in combined for c  in crypto_kws)

        return has_short_term and has_crypto

    def filter_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        qualified = []
        short_term_count = 0
        
        logger.info("Filtering markets with criteria:")
        logger.info(f"  - Crypto: {self.enable_crypto}")
        logger.info(f"  - Finance: {self.enable_finance}")
        logger.info(f"  - Politics: {self.enable_politics}")
        logger.info(f"  - Sports: {self.enable_sports}")
        logger.info(f"  - Min Vol: ${self.min_volume:,.0f}, Min Liq: ${self.min_liquidity:,.0f}, Max Spread: {self.max_spread:.2%}")

        for market in markets:
            try:
                question = (market.get("question") or "").lower()
                
                # Check global blocklist first (most efficient)
                blocked_kw = next((k for k in self.BLOCK_KEYWORDS if k in question), None)
                if blocked_kw:
                    # Exception: Allow "Up or Down" even if it somehow matches a blocklist word (unlikely but safe)
                    if "up or down" not in question:
                        continue
                
                # Basic metrics
                volume = float(market.get("volume", 0))
                liquidity = float(market.get("liquidity") or market.get("liquidityNum") or market.get("liquidityClob") or 0)
                spread = self.calculate_spread(market)
                
                # Classification and Category Filtering
                category = self.classify_market(market)
                
                # 1. Short-Term Crypto Exception (Relaxed Filters)
                if self.is_short_term_crypto(market):
                    # Relaxed thresholds for 5min/15min markets
                    # Vol >= 300, Liq >= 30, Spread <= 25%
                    if volume >= 300 and liquidity >= 30 and spread <= 0.25:
                        market["mapped_category"] = "crypto" # Force correct category
                        qualified.append(market)
                        short_term_count += 1
                        logger.info(f"✅ Accepted short-term market: {question[:50]}... Vol:{volume:.0f} Liq:{liquidity:.0f}")
                        continue
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(
                                f"❌ Short-term rejeitado: '{question[:55]}' "
                                f"Vol:{volume:.0f} Liq:{liquidity:.0f} Spread:{spread:.2%} "
                                f"(min_vol={300}, min_liq={30}, max_spread=25%)"
                            )

                # 2. Standard Filters (Strict)
                if volume < self.min_volume: continue
                if liquidity < self.min_liquidity: continue
                if spread > self.max_spread: continue
                
                is_allowed = False
                if category == "crypto" and self.enable_crypto: is_allowed = True
                elif category == "finance" and self.enable_finance: is_allowed = True
                elif category == "politics" and self.enable_politics: is_allowed = True
                elif category == "sports" and self.enable_sports: is_allowed = True
                
                if is_allowed:
                    market["mapped_category"] = category
                    qualified.append(market)
                    
            except Exception as e:
                logger.error(f"Error filtering market: {e}")
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

if __name__ == "__main__":
    # Setup basic logging when running standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Starting market discovery...")
    discovery = MarketDiscovery()
    markets = discovery.run()
    save_markets(markets)
    print(f"Done. Found {len(markets)} markets.")
