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
        """
        if signal["action"] == "hold" or signal["action"] == "skip":
            return {"success": False, "reason": "Signal is hold/skip"}
            
        amount = signal.get("suggested_amount", 0.0)
        # Proteção contra tipo inválido de amount
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            # Tenta limpar se vier como string formatada (ex: "$10.00")
            if isinstance(amount, str):
                import re
                amount = float(re.sub(r'[^\d.]', '', amount) or 0.0)
            else:
                return {"success": False, "reason": f"Invalid amount type: {amount} ({type(amount)})"}

        if amount <= 0:
            return {"success": False, "reason": "Zero amount"}

        try:
            # Importa aqui para evitar dependência circular no topo
            from execution_engine import execute_trade
            import config
            import json
            import os

            # Tenta carregar a chave de API correta para este bot
            api_key = None
            
            # Se o bot tiver um slot de chave atribuído (seja via atributo ou inferido pelo nome)
            # Mas o BaseBot padrão não tem self._api_key_slot definido explicitamente na init.
            # O arena.py gerencia isso externamente na maioria das vezes, mas aqui estamos dentro do bot.
            
            # Tenta carregar do arquivo de chaves de bots
            try:
                if os.path.exists(config.SIMMER_BOT_KEYS_PATH):
                    with open(config.SIMMER_BOT_KEYS_PATH, 'r') as f:
                        keys = json.load(f)
                        # Tenta encontrar a chave pelo nome do bot se o slot não estiver definido
                        # Mas o arquivo mapeia slot_id -> key.
                        # Precisamos saber qual slot este bot ocupa.
                        # O arena.py sabe. O bot não sabe seu slot nativamente.
                        pass
            except Exception:
                pass
            
            # Fallback para a chave padrão (Single Account Mode)
            if not api_key and os.path.exists(config.SIMMER_API_KEY_PATH):
                with open(config.SIMMER_API_KEY_PATH, 'r') as f:
                    api_key = f.read().strip()

            # Chama a função de execução global
            # execute_trade(bot_name, market_id, side, amount, price=None, order_type="market", api_key=None)
            
            market_id = market.get("condition_id") or market.get("id")
            side = signal.get("side", "yes") # Default to yes if missing
            
            # Preço limite opcional (se o bot definir 'limit_price')
            # Se não, usa None (Market Order simulada)
            price = signal.get("limit_price") 
            
            return execute_trade(
                bot_name=self.name,
                market_id=market_id,
                side=side,
                amount=amount,
                price=price,
                api_key=api_key
            )
            
        except Exception as e:
            return {"success": False, "reason": f"Execution error in BaseBot: {e}"}

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
