import logging
import time
from typing import Dict, Any, Optional
from strategies.base_bot import BaseBot
import polymarket_client

logger = logging.getLogger(__name__)

DEFAULT_PARAMS = {
    "min_profit_threshold": 0.005, # 0.5%
    "max_position_size": 100,
    "min_liquidity": 5000,
}

class ArbitrageBot(BaseBot):
    """
    Pure Arbitrage Bot (Gabagool-style).
    Monitors for ask_yes + ask_no < 0.99.
    """
    def __init__(self, name="arbitrage-v1", params=None, generation=0, lineage=None):
        super().__init__(
            name=name,
            strategy_type="arbitrage",
            params=params or DEFAULT_PARAMS.copy(),
            generation=generation,
            lineage=lineage,
        )

    def analyze(self, market: dict, signals: dict, kelly_fraction=None) -> dict:
        """
        Check for arbitrage opportunity in the given market.
        """
        # 1. Get Token IDs
        tokens = market.get("clobTokenIds")
        if not tokens or len(tokens) < 2:
            return self._hold("Missing token IDs")
        
        token_yes = tokens[0]
        token_no = tokens[1]
        
        # 2. Get Order Books (Real-time)
        try:
            # In a real low-latency setup, this would access a local cache updated by WS
            book_yes = polymarket_client.get_order_book(token_yes)
            book_no = polymarket_client.get_order_book(token_no)
        except Exception as e:
            return self._hold(f"Error fetching books: {e}")

        if not book_yes or not book_no:
            return self._hold("Empty order books")
            
        # 3. Get Best Asks & Liquidity Check
        try:
            if not book_yes.asks or not book_no.asks:
                 return self._hold("No asks")

            best_ask_yes = float(book_yes.asks[0].price)
            best_ask_no = float(book_no.asks[0].price)
            
            # Liquidity Filter (Gabagool-style)
            # Check if there is enough depth at the best price (or near it)
            min_liq = self.strategy_params.get("min_liquidity", 5000)
            
            # Calculate approx liquidity at top level
            # This is simplified; robust check would walk the book
            yes_depth_val = float(book_yes.asks[0].size) * best_ask_yes
            no_depth_val = float(book_no.asks[0].size) * best_ask_no
            
            # If top level is thin, we might skip or check next levels
            # Gabagool logic: "only operate if depth > $5k"
            # We'll check if available size * price > min_liq
            # Note: 5k is high for a single level, maybe it meant total book depth?
            # Or cumulative depth. Let's use a more lenient check for "top of book" liquidity
            # to start, or accumulate top 3 levels.
            
            def get_depth(asks, levels=3):
                total_val = 0.0
                for a in asks[:levels]:
                    total_val += float(a.size) * float(a.price)
                return total_val
                
            yes_depth_total = get_depth(book_yes.asks)
            no_depth_total = get_depth(book_no.asks)
            
            if yes_depth_total < min_liq or no_depth_total < min_liq:
                 return self._hold(f"Low liquidity: Y=${yes_depth_total:.0f} N=${no_depth_total:.0f}")

        except (AttributeError, IndexError, ValueError) as e:
             return self._hold(f"Invalid book data: {e}")

        # 5. Check Arbitrage Condition
        combined_cost = best_ask_yes + best_ask_no
        
        threshold = self.strategy_params.get("min_profit_threshold", 0.005)
        
        if combined_cost < (1.0 - threshold):
            profit = 1.0 - combined_cost
            return {
                "action": "buy",
                "side": "both", # Indicates arbitrage execution
                "confidence": 1.0,
                "reasoning": f"ARB: Cost {combined_cost:.4f}, Profit {profit:.4f}",
                "suggested_amount": self.strategy_params.get("max_position_size", 100),
                "meta": {
                    "token_yes": token_yes,
                    "token_no": token_no,
                    "price_yes": best_ask_yes,
                    "price_no": best_ask_no
                }
            }

        return self._hold(f"No arb. Cost: {combined_cost:.4f}")

    def _hold(self, reason):
        return {
            "action": "hold",
            "confidence": 0.0,
            "reasoning": reason,
            "suggested_amount": 0.0
        }
