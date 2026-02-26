import os
import base64
import logging
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class MarketDiscovery:
    """
    Motor de descoberta de mercados v3.1
    - Gamma API para mercados de longo prazo
    - CLOB API para mercados Up or Down de curto prazo (15min/1h)
    """

    def __init__(self,
                 enable_crypto: bool = True,
                 enable_finance: bool = True,
                 enable_politics: bool = False,
                 enable_sports: bool = False,
                 min_volume: float = None,
                 min_liquidity: float = None,
                 max_spread: float = None):

        self.enable_crypto   = enable_crypto
        self.enable_finance  = enable_finance
        self.enable_politics = enable_politics
        self.enable_sports   = enable_sports

        self.min_volume    = min_volume    if min_volume    is not None else getattr(config, "MIN_MARKET_VOLUME", 50000)
        self.min_liquidity = min_liquidity if min_liquidity is not None else getattr(config, "MIN_LIQUIDITY", 0.0)
        self.max_spread    = max_spread    if max_spread    is not None else getattr(config, "MAX_MARKET_SPREAD", 0.05)

        self.KEYWORDS = {
            "crypto": [
                "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
                "crypto", "token", "nft", "defi", "xrp", "ripple",
                "bnb", "avax", "doge", "matic", "up or down", "updown"
            ],
            "finance": ["fed", "inflation", "interest rate", "cpi", "gdp", "recession",
                        "treasury", "s&p 500", "nasdaq", "dow jones", "stock", "ipo",
                        "oil", "gold", "silver", "eur", "usd", "yield"],
            "politics": ["trump", "biden", "harris", "election", "poll", "vote",
                         "senate", "house", "president", "democrat", "republican"],
            "sports": ["nba", "nfl", "nhl", "mlb", "soccer", "cup",
                       "game", "league", "tournament", "champion"]
        }

        self.BLOCK_KEYWORDS = [
            "israel", "gaza", "hamas", "ukraine", "russia", "war", "death", "kill",
            "trump", "biden", "harris", "election", "president", "senate", "house",
            "taylor swift", "kanye", "drake", "movie", "box office", "song", "album",
            "weather", "temperature", "earthquake", "hurricane"
        ]

    # ------------------------------------------------------------------ #
    #  CLOB API — mercados Up or Down                                      #
    # ------------------------------------------------------------------ #

    def _normalize_clob_market(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza campos da CLOB API para o formato esperado pelo filtro."""
        m["slug"]    = m.get("market_slug", m.get("slug", ""))
        m["endDate"] = m.get("end_date_iso", "")
        m["active"]  = m.get("active", False)
        m["closed"]  = m.get("closed", False)
        m.setdefault("volume", 0)
        m.setdefault("liquidity", 0)

        tokens = m.get("tokens", [])
        if len(tokens) == 2:
            try:
                p0 = float(tokens[0].get("price", 0) or 0)
                p1 = float(tokens[1].get("price", 0) or 0)
                total = p0 + p1
                m["spread"] = abs(1.0 - total) if total > 0 else 1.0
            except Exception:
                m["spread"] = 1.0
        else:
            m["spread"] = 1.0

        # current_price = preço do token YES
        if tokens:
            try:
                yes_tok = next((t for t in tokens if (t.get("outcome") or "").lower() == "up"), tokens[0])
                m["current_price"] = float(yes_tok.get("price", 0.5) or 0.5)
            except Exception:
                m["current_price"] = 0.5

        return m

    def _find_active_clob_offset(self, headers: Dict) -> Optional[int]:
        """
        Busca binária para achar offset com mercados Up or Down aceitando ordens.
        Mercados recentes ficam em offsets altos (400k-700k em fev/2026).
        """
        # Passo 1: acha o fim dos dados com passos de 100k
        logger.info("  Localizando offset ativo na CLOB API...")
        lo, hi = 300000, 1000000
        last_with_data = 300000

        for offset in range(300000, 1000000, 100000):
            cursor = base64.b64encode(str(offset).encode()).decode()
            try:
                r = requests.get("https://clob.polymarket.com/markets",
                                 params={"limit": 10, "next_cursor": cursor},
                                 headers=headers, timeout=10)
                data = r.json().get("data", []) if r.status_code == 200 else []
                if not data:
                    hi = offset
                    logger.info(f"  Fim dos dados em offset ~{offset}")
                    break
                last_with_data = offset
                lo = offset
            except Exception:
                break

        hi = min(hi, last_with_data + 100000)

        # Passo 2: busca binária entre lo e hi
        logger.info(f"  Busca binária entre {lo} e {hi}...")
        best = None
        for _ in range(12):
            mid = (lo + hi) // 2
            cursor = base64.b64encode(str(mid).encode()).decode()
            try:
                r = requests.get("https://clob.polymarket.com/markets",
                                 params={"limit": 200, "next_cursor": cursor},
                                 headers=headers, timeout=15)
                if r.status_code != 200:
                    hi = mid
                    continue
                data = r.json().get("data", [])
                if not data:
                    hi = mid
                    continue

                accepting = [m for m in data
                             if m.get("accepting_orders")
                             and "up or down" in (m.get("question") or "").lower()]
                logger.info(f"  Offset {mid}: {len(data)} mercados, {len(accepting)} up/down ativos")

                if accepting:
                    best = mid
                    hi = mid
                else:
                    sample_date = (data[0].get("end_date_iso") or "") if data else ""
                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    if sample_date and sample_date < now_str:
                        lo = mid
                    else:
                        hi = mid
            except Exception as e:
                logger.warning(f"  Erro offset {mid}: {e}")
                hi = mid

            if hi - lo < 500:
                break

        return best if best is not None else lo

    def fetch_clob_updown_markets(self) -> List[Dict[str, Any]]:
        """Busca mercados Up or Down ativos na CLOB API."""
        headers = {"User-Agent": "PolymarketBotArena/3.1"}
        found = []

        logger.info("Buscando mercados Up or Down na CLOB API...")
        start_offset = self._find_active_clob_offset(headers)
        if start_offset is None:
            logger.warning("  Não foi possível localizar offset ativo.")
            return []

        logger.info(f"  Varrendo a partir do offset {start_offset}...")
        cursor = base64.b64encode(str(start_offset).encode()).decode()

        for page in range(8):  # máx 8 * 1000 = 8000 mercados
            try:
                r = requests.get("https://clob.polymarket.com/markets",
                                 params={"limit": 1000, "next_cursor": cursor},
                                 headers=headers, timeout=20)
                if r.status_code != 200:
                    break
                resp = r.json()
                data = resp.get("data", [])
                next_cursor = resp.get("next_cursor", "")

                updown_active = [
                    m for m in data
                    if "up or down" in (m.get("question") or "").lower()
                    and m.get("accepting_orders", False)
                    and not m.get("closed", True)
                ]

                for m in updown_active:
                    found.append(self._normalize_clob_market(m))

                logger.info(f"  Página {page+1}: {len(data)} mercados, {len(updown_active)} up/down ativos")

                if not next_cursor or next_cursor == cursor or not data:
                    break
                cursor = next_cursor

            except Exception as e:
                logger.warning(f"  Erro página CLOB: {e}")
                break

        logger.info(f"  Total Up or Down ativos (CLOB): {len(found)}")
        return found

    # ------------------------------------------------------------------ #
    #  Gamma API — mercados de longo prazo                                 #
    # ------------------------------------------------------------------ #

    def fetch_active_markets(self, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Gamma API (longo prazo) + CLOB API (Up or Down curto prazo)."""
        all_markets = []
        page = 0
        headers = {"User-Agent": "PolymarketBotArena/3.1"}

        try:
            logger.info("Fetching active markets from Gamma Markets API...")
            now = datetime.now(timezone.utc)
            start_date  = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            future_date = (now + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

            while page < max_pages:
                params = {
                    "limit": 100, "offset": page * 100,
                    "endDateMin": start_date, "endDateMax": future_date,
                    "active": "true", "closed": "false", "archived": "false",
                    "orderBy": "liquidity", "orderDirection": "desc"
                }
                response = requests.get("https://gamma-api.polymarket.com/markets",
                                        params=params, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                if not data:
                    break
                all_markets.extend(data)
                if len(data) < 100:
                    break
                page += 1

            logger.info(f"Gamma API: {len(all_markets)} mercados.")

            # CLOB — Up or Down de curto prazo
            if self.enable_crypto:
                clob_markets = self.fetch_clob_updown_markets()
                existing_slugs = {m.get("slug", "") for m in all_markets}
                added = 0
                for m in clob_markets:
                    slug = m.get("slug", "")
                    if slug not in existing_slugs:
                        all_markets.append(m)
                        existing_slugs.add(slug)
                        added += 1
                logger.info(f"CLOB: adicionados {added} mercados Up or Down.")

            logger.info(f"Successfully fetched {len(all_markets)} raw markets.")
            return all_markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Classificação e filtros                                             #
    # ------------------------------------------------------------------ #

    def calculate_spread(self, market: Dict[str, Any]) -> float:
        api_spread = market.get("spread")
        if api_spread is not None:
            try:
                return float(api_spread)
            except (ValueError, TypeError):
                pass
        try:
            best_bid = float(market.get("bestBid", 0) or 0)
            best_ask = float(market.get("bestAsk", 0) or 0)
            if best_bid > 0 and best_ask > 0:
                return (best_ask - best_bid) / best_ask
        except (ValueError, TypeError):
            pass
        return 1.0

    def classify_market(self, market: Dict[str, Any]) -> str:
        question = (market.get("question") or "").lower()
        category = (market.get("category") or "").lower()
        tags     = [t.lower() for t in (market.get("tags_list") or market.get("tags") or [])]
        for cat, keywords in self.KEYWORDS.items():
            if any(k in question for k in keywords): return cat
            if any(k in category for k in keywords): return cat
            if tags and any(k in " ".join(tags) for k in keywords): return cat
        return "unknown"

    def is_short_term_crypto(self, market: Dict[str, Any]) -> bool:
        title    = (market.get("question") or market.get("title") or "").lower()
        slug     = (market.get("slug") or market.get("market_slug") or "").lower()
        tags     = [t.lower() for t in (market.get("tags_list") or market.get("tags") or [])]
        combined = title + " " + slug + " " + " ".join(tags)

        short_term_kws = ['5 min', '5 minutes', '15 min', '15 minutes', '5m', '15m',
                          '1h', '4h', 'next 5', 'next 15', 'up or down', 'updown',
                          'up-or-down', 'recurring']
        crypto_kws = ['bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol',
                      'xrp', 'ripple', 'bnb', 'avax', 'doge', 'matic', 'crypto']

        return (any(kw in combined for kw in short_term_kws) and
                any(c  in combined for c  in crypto_kws))

    def filter_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        qualified = []
        short_term_count = 0

        logger.info("Filtering markets with criteria:")
        logger.info(f"  - Crypto: {self.enable_crypto}, Finance: {self.enable_finance}, "
                    f"Politics: {self.enable_politics}, Sports: {self.enable_sports}")
        logger.info(f"  - Min Vol: ${self.min_volume:,.0f}, Min Liq: ${self.min_liquidity:,.0f}, "
                    f"Max Spread: {self.max_spread:.2%}")

        for market in markets:
            try:
                question = (market.get("question") or "").lower()

                # Blocklist (exceto Up or Down)
                if "up or down" not in question:
                    if any(k in question for k in self.BLOCK_KEYWORDS):
                        continue

                volume    = float(market.get("volume",    0) or 0)
                liquidity = float(market.get("liquidity") or market.get("liquidityNum") or
                                  market.get("liquidityClob") or 0)
                spread    = self.calculate_spread(market)
                category  = self.classify_market(market)

                # Mercados Up or Down da CLOB: accepting_orders=True → aceita direto
                if self.is_short_term_crypto(market):
                    if market.get("accepting_orders", False):
                        market["mapped_category"] = "crypto"
                        qualified.append(market)
                        short_term_count += 1
                        logger.info(f"✅ Up or Down ativo: {question[:65]}")
                        continue
                    # Veio da Gamma (tem volume/liq)
                    if volume >= 300 and liquidity >= 30 and spread <= 0.25:
                        market["mapped_category"] = "crypto"
                        qualified.append(market)
                        short_term_count += 1
                        continue
                    logger.debug(f"❌ Short-term rejeitado: '{question[:55]}' "
                                 f"Vol:{volume:.0f} Liq:{liquidity:.0f} Spread:{spread:.2%}")
                    continue

                # Filtros padrão
                if volume    < self.min_volume:    continue
                if liquidity < self.min_liquidity: continue
                if spread    > self.max_spread:    continue

                is_allowed = (
                    (category == "crypto"   and self.enable_crypto)   or
                    (category == "finance"  and self.enable_finance)  or
                    (category == "politics" and self.enable_politics) or
                    (category == "sports"   and self.enable_sports)
                )
                if is_allowed:
                    market["mapped_category"] = category
                    qualified.append(market)

            except Exception as e:
                logger.error(f"Error filtering market: {e}")

        qualified.sort(key=lambda x: float(x.get("liquidity", 0) or 0), reverse=True)
        logger.info(f"Found {len(qualified)} qualified markets "
                    f"({short_term_count} Up or Down curto prazo).")
        return qualified

    def run(self) -> List[Dict[str, Any]]:
        raw = self.fetch_active_markets()
        return self.filter_markets(raw)


def save_markets(markets: List[Dict[str, Any]], filename: str = "qualified_markets.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(markets, f, indent=2)
        logger.info(f"Saved {len(markets)} markets to {filename}")
    except Exception as e:
        logger.error(f"Failed to save: {e}")


def run_scan_and_save():
    """Wrapper de compatibilidade para arena.py."""
    try:
        discovery = MarketDiscovery(
            enable_crypto   = os.getenv("ENABLE_CRYPTO",   "true").lower()  == "true",
            enable_finance  = os.getenv("ENABLE_FINANCE",  "true").lower()  == "true",
            enable_politics = os.getenv("ENABLE_POLITICS", "false").lower() == "true",
            enable_sports   = os.getenv("ENABLE_SPORTS",   "false").lower() == "true",
        )
        markets = discovery.run()
        save_markets(markets)
        return True
    except Exception as e:
        logging.error(f"run_scan_and_save error: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("Starting market discovery...")
    discovery = MarketDiscovery()
    markets = discovery.run()
    save_markets(markets)
    print(f"Done. Found {len(markets)} markets.")
