"""
advanced_whale_copy_trader.py - Módulo para Copytrading Inteligente de Whales no Polymarket Bot Arena v3.0

Funcionalidades principais:
- Rastreamento automático de top whales via Polymarket API/on-chain data.
- Filtro LLM (Grok/Claude/Gemini API) para validar trades com base em notícias atuais.
- Cópia inteligente de trades aprovados com position sizing via RiskManager.
- Integração com evolução genética (whales como "bots virtuais").
- Notificações Telegram e registro no SQLite.
- Execução com limit orders + post-only para minimizar slippage.

Compatibilidade: Integra com arena.py, polymarket_client.py, config.py, risk_manager.py, telegram_notifier.py, db.py.

Requisitos:
- Env vars: GROK_API_KEY, CLAUDE_API_KEY ou GEMINI_API_KEY para LLM.
- Bibliotecas: requests, json, datetime, logging, asyncio, google-generativeai (já no requirements.txt).

Uso em arena.py:
from advanced_whale_copy_trader import WhaleCopyTrader
whale_trader = WhaleCopyTrader()
signals = whale_trader.get_whale_signals(markets)
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional

# Importação para Gemini
import google.generativeai as genai

# Importações do projeto (assumindo estrutura existente)
from config import (
    POLYMARKET_API_URL,  # Ex: "https://clob.polymarket.com" ou Simmer equivalente
    MIN_WIN_RATE,  # 0.7
    MIN_WHALE_VOLUME,  # 50000
    TOP_WHALES_COUNT,  # 30
    LLM_PROVIDER,  # "grok", "claude" ou "gemini"
    LLM_API_KEY,  # De .env (genérico para o provider escolhido)
    MIN_LLM_CONFIDENCE,  # 0.75
    TRADE_MIN_EV_AFTER_COSTS,  # 0.045
)
from polymarket_client import place_limit_order, estimate_gas, calculate_slippage
from core.risk_manager import RiskManager
from telegram_notifier import send_telegram_message
from db import save_trade_to_db, get_historical_resolutions
from signals.sentiment import get_current_news_summary  # Para contexto LLM

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WhaleCopyTrader:
    def __init__(self, risk_manager: Optional[RiskManager] = None):
        self.risk_manager = risk_manager or RiskManager()  # Centralizado
        self.whales_cache: Dict[str, Dict] = {}  # Cache de whales {wallet: {win_rate, volume, last_trades}}
        self.last_update: datetime = datetime.min
        self.llm_provider = LLM_PROVIDER
        self.llm_api_key = LLM_API_KEY
        if self.llm_provider == "gemini":
            genai.configure(api_key=self.llm_api_key)  # Configura Gemini globalmente
        self.update_whales()  # Inicializa cache

    async def update_whales(self) -> None:
        """Atualiza lista de top whales via Polymarket API/on-chain (simulado ou real)."""
        if (datetime.now() - self.last_update) < timedelta(hours=1):
            return  # Cache válido por 1h

        try:
            # Fetch whales: Use API para top traders (exemplo fictício; adapte para real Polymarket/Simmer)
            resp = requests.get(
                f"{POLYMARKET_API_URL}/traders/top?limit={TOP_WHALES_COUNT}&min_volume={MIN_WHALE_VOLUME}",
                timeout=10
            )
            resp.raise_for_status()
            traders = resp.json().get("traders", [])

            for trader in traders:
                wallet = trader["wallet"]
                trades = trader.get("trades", [])  # Últimos 100 trades
                resolved_trades = [t for t in trades if t["resolved"]]
                win_count = sum(1 for t in resolved_trades if t["pnl"] > 0)
                win_rate = win_count / len(resolved_trades) if resolved_trades else 0

                if win_rate >= MIN_WIN_RATE:
                    self.whales_cache[wallet] = {
                        "win_rate": win_rate,
                        "volume": trader["total_volume"],
                        "last_trades": trades[-10:],  # Últimos 10 para cópia
                    }

            logger.info(f"Updated {len(self.whales_cache)} whales with win_rate > {MIN_WIN_RATE*100}%")
            self.last_update = datetime.now()

        except Exception as e:
            logger.error(f"Error updating whales: {e}")

    async def get_llm_filter(self, trade: Dict, market: Dict) -> bool:
        """Filtro LLM: Verifica se trade faz sentido com notícias atuais. Suporte a Gemini adicionado."""
        if not self.llm_api_key:
            logger.warning("LLM API key missing - skipping filter")
            return True

        # Contexto: Notícias + on-chain + market info
        news_summary = await get_current_news_summary(market["question"])  # De signals.sentiment
        prompt = f"""
Analise se esse trade faz sentido com notícias atuais (Twitter/news/on-chain).
Trade: {json.dumps(trade, indent=2)}
Market: {market["question"]} (prob yes: {market["yes_prob"]}, no: {market["no_prob"]})
Notícias recentes: {news_summary}

Responda em JSON: {{"valid": true/false, "confidence": 0-1, "reason": "curta razão"}}
"""

        try:
            if self.llm_provider == "grok":
                url = "https://api.grok.xai.com/v1/chat/completions"  # Exemplo; adapte
                headers = {"Authorization": f"Bearer {self.llm_api_key}"}
                data = {"model": "grok-4", "messages": [{"role": "user", "content": prompt}]}
                resp = requests.post(url, json=data, headers=headers, timeout=20)
            elif self.llm_provider == "claude":
                url = "https://api.anthropic.com/v1/messages"
                headers = {"x-api-key": self.llm_api_key, "anthropic-version": "2023-06-01"}
                data = {"model": "claude-3-opus-20240229", "max_tokens": 100, "messages": [{"role": "user", "content": prompt}]}
                resp = requests.post(url, json=data, headers=headers, timeout=20)
            elif self.llm_provider == "gemini":
                model = genai.GenerativeModel('gemini-1.5-flash')  # Ou 'gemini-pro' se preferir
                response = model.generate_content(prompt)
                result = response.text  # Gemini retorna texto direto
                resp = None  # Não usa requests, mas processa abaixo
            else:
                raise ValueError("LLM provider inválido")

            if self.llm_provider != "gemini":
                resp.raise_for_status()
                result = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")

            parsed = json.loads(result)

            valid = parsed.get("valid", False) and parsed.get("confidence", 0) >= MIN_LLM_CONFIDENCE
            logger.info(f"LLM filter ({self.llm_provider}): {valid} (confidence: {parsed['confidence']}) - {parsed['reason']}")
            return valid

        except Exception as e:
            logger.error(f"LLM filter error ({self.llm_provider}): {e}")
            return False  # Conservador: rejeita se erro

    async def get_whale_signals(self, markets: List[Dict]) -> List[Dict]:
        """Gera sinais de copytrading baseados em whales para os mercados."""
        await self.update_whales()
        signals = []

        for wallet, data in self.whales_cache.items():
            for whale_trade in data["last_trades"]:
                market_id = whale_trade["market_id"]
                market = next((m for m in markets if m["id"] == market_id), None)
                if not market:
                    continue

                # Valida EV após custos
                expected_ev = self.calculate_expected_ev(whale_trade, market)
                if expected_ev < TRADE_MIN_EV_AFTER_COSTS:
                    continue

                # Filtro LLM
                if not await self.get_llm_filter(whale_trade, market):
                    continue

                # Gera sinal
                signal = {
                    "bot_name": f"whale_copy_{wallet[:6]}",
                    "market_id": market_id,
                    "side": whale_trade["side"],  # "yes" or "no"
                    "size": self.risk_manager.calculate_position_size(expected_ev, market["volatility"]),
                    "entry_price": whale_trade["entry_price"],
                    "expected_ev": expected_ev,
                }
                signals.append(signal)

        return signals

    def calculate_expected_ev(self, trade: Dict, market: Dict) -> float:
        """Calcula EV esperado após custos (spread, gas, slippage)."""
        spread = market["spread"]
        gas_est = estimate_gas(trade["size"])
        slippage_est = calculate_slippage(market["liquidity"], trade["size"])

        raw_ev = trade["expected_profit"] / trade["size"]  # Simplificado
        costs = spread + (gas_est / trade["size"]) + slippage_est
        return raw_ev - costs

    async def execute_copy_trade(self, signal: Dict, api_key: str) -> bool:
        """Executa o trade copiado com limit order."""
        try:
            # Position sizing final via RiskManager
            if not self.risk_manager.can_trade(signal["bot_name"], signal["size"]):
                logger.warning(f"Risk limit reached for {signal['bot_name']}")
                return False

            # Place limit order
            order_id = place_limit_order(
                market_id=signal["market_id"],
                side=signal["side"],
                size=signal["size"],
                price=signal["entry_price"] * 0.99,  # 1% below para post-only
                api_key=api_key,
                post_only=True,
            )

            # Registro e notificação
            trade_data = {**signal, "order_id": order_id, "timestamp": datetime.now().isoformat()}
            save_trade_to_db(trade_data)
            await send_telegram_message(f"📈 Copiado whale trade: {signal['market_id']} {signal['side']} size {signal['size']:.2f}")

            # Para evolução: Registra como "bot virtual"
            self.register_for_evolution(signal["bot_name"], trade_data)

            return True

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return False

    def register_for_evolution(self, bot_name: str, trade_data: Dict) -> None:
        """Registra whale como bot virtual para evolução genética."""
        # Integra com bot_evolution_manager.py (exemplo)
        from evolution_integration import register_virtual_bot
        register_virtual_bot(bot_name, trade_data)

# Exemplo de uso standalone (para testes)
if __name__ == "__main__":
    async def test():
        trader = WhaleCopyTrader()
        # Simule markets
        markets = [{"id": "123", "question": "Trump wins 2028?", "yes_prob": 0.55, "no_prob": 0.45, "spread": 0.015, "liquidity": 250000, "volatility": 0.12}]
        signals = await trader.get_whale_signals(markets)
        if signals:
            await trader.execute_copy_trade(signals[0], "test_api_key")

    asyncio.run(test())