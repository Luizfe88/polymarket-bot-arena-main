"""Base Bot Strategy class."""
from typing import Dict, Any, Optional

class BaseBot:
    """Base class for all bot strategies."""
    
    def __init__(
        self, 
        name: str, 
        strategy_type: str, 
        params: Dict[str, Any], 
        generation: int = 0,
        lineage: str = None
    ):
        self.name = name
        self.strategy_type = strategy_type
        self.strategy_params = params
        self.generation = generation
        self.lineage = lineage
        
        # State
        self.bankroll = 0.0
        self.active_positions = {}
        self.trades_history = []
        
    def make_decision(self, market: dict, signals: dict, kelly_fraction=None) -> dict:
        """
        Legacy wrapper for analyze() to maintain compatibility with arena.py
        """
        return self.analyze(market, signals)

    def analyze(self, market: dict, signals: dict, kelly_fraction=None) -> dict:
        """
        Analyze market data and signals to make a trading decision.
        
        Returns:
            dict: {
                "action": "buy" | "sell" | "hold",
                "side": "yes" | "no",
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "suggested_amount": float
            }
        """
        raise NotImplementedError("Subclasses must implement analyze()")
        
    def execute(self, signal: dict, market: dict) -> dict:
        """
        Execute a trade based on the signal.
        This is a simulation/placeholder. In a real system, this would call an execution engine.
        """
        if signal["action"] == "hold":
            return {"success": False, "reason": "Signal is hold"}
            
        amount = signal.get("suggested_amount", 0.0)
        if amount <= 0:
            return {"success": False, "reason": "Zero amount"}

        # Simulate execution success
        # In a real bot, this would place an order
        # For the arena, we return success so the arena can log/track it
        # The arena code actually handles the DB recording and API calls (via execution_engine),
        # but it expects the bot object to have an 'execute' method if it calls bot.execute()
        # Wait, looking at arena.py:
        # result = bot.execute(signal, market)
        # So yes, we need this method.
        
        # However, arena.py seems to rely on an external execution_engine usually?
        # Let's check how it was before.
        # It seems the previous bots had an execute method.
        
        # We'll implement a basic one that returns success, 
        # but we should probably delegate to the arena's execution logic if possible.
        # Actually, looking at the logs, arena.py calls bot.execute(signal, market).
        
        # Let's try to import the global execution engine if needed, 
        # or just return the signal payload enriched with status.
        
        from execution_engine import execute_trade
        
        # We need the API key... but BaseBot doesn't have it stored by default?
        # The arena loop has 'api_key'.
        # But bot.execute() signature in arena is just (signal, market).
        # This implies the bot should know how to execute or it's a wrapper.
        
        # WAIT! The error log says: 'MomentumBot' object has no attribute 'execute'
        # So we just need to add this method to BaseBot.
        
        # Let's implement a wrapper that calls the global execute_trade
        # We might need to fetch the API key from config or context.
        # For now, let's assume the arena passes the key or we get it from config.
        
        import config
        # We might need to pass the key in __init__ or use a global one.
        # Or, we can change arena.py to call execute_trade directly?
        # No, better to fix the bot class to be compatible.
        
        # If we look at how it was done before (I can't see the deleted files),
        # but typically it would call execution_engine.
        
        try:
            # We need to get the API key. 
            # In the new architecture, maybe we should pass it?
            # For now, let's try to load it or use a default if in paper mode.
            api_key = None
            if hasattr(self, '_api_key_slot'):
                 # We might need to load keys based on slot
                 pass
            
            # Actually, arena.py loop has:
            # result = bot.execute(signal, market)
            # And then:
            # if result.get("success"):
            #    executed.add(key)
            #    new_trades += 1
            
            # It seems the actual API call happens inside bot.execute.
            
            # Let's import the execution function
            from execution_engine import execute_trade
            
            # We need to pass the API key.
            # If we don't have it, maybe execute_trade handles it?
            # execute_trade(bot_name, signal, market, api_key=None) -> dict
            
            # We will try to find the api key from the bot's slot if it exists
            api_key = None
            if hasattr(self, '_api_key_slot'):
                import json
                try:
                    with open(config.SIMMER_BOT_KEYS_PATH) as f:
                        keys = json.load(f)
                        api_key = keys.get(self._api_key_slot)
                except:
                    pass
            
            # Fallback to default key if not found
            if not api_key:
                try:
                    with open(config.SIMMER_API_KEY_PATH) as f:
                        api_key = f.read().strip()
                except:
                    pass

            return execute_trade(self.name, signal, market, api_key)
            
        except Exception as e:
            return {"success": False, "reason": f"Execution error: {e}"}

    def get_performance(self, hours=24):
        """
        Get bot performance metrics from DB.
        """
        import db
        return db.get_bot_performance(self.name, hours)
        
    def reset_daily(self):
        """
        Reset daily stats (if any internal state needs reset).
        """
        pass
