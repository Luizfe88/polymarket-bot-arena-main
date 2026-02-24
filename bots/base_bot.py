"""Abstract base class all arena bots inherit from."""

import json
import random
import copy
import math
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logging_config import setup_logging_with_brt
import db
import learning
import edge_model
from telegram_notifier import get_telegram_notifier
from core.risk_manager import risk_manager

logger = setup_logging_with_brt(__name__)


class BaseBot(ABC):
    name: str
    strategy_type: str
    strategy_params: dict
    generation: int
    lineage: str

    # Exit strategy: None = hold to resolution (default)
    # "stop_loss" = exit when position is down stop_loss_pct
    # "take_profit" = exit when position is up take_profit_pct
    exit_strategy: str = None
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0

    # Each strategy type gets different parameters for differentiation.
    # This creates real competition for evolution to select from.
    STRATEGY_PRIORS = {
        "momentum": 0.52,       # slight YES bias — momentum tends bullish
        "mean_reversion": 0.48, # slight NO bias — mean reversion bets against crowd
        "mean_reversion_sl": 0.48,
        "mean_reversion_tp": 0.48,
        "sentiment": 0.50,      # neutral
        "hybrid": 0.50,         # neutral
        "orderflow": 0.50,
    }
    # How aggressively each strategy trusts the market price signal
    MARKET_PRICE_AGGRESSION = {
        "momentum": 1.2,        # follows market price strongly
        "mean_reversion": 0.95, # nearly follows market (contrarian was -$16 loser)
        "mean_reversion_sl": 0.95,
        "mean_reversion_tp": 0.95,
        "sentiment": 1.0,       # neutral
        "hybrid": 1.0,          # neutral (was 0.9, contrarian loses)
        "orderflow": 1.0,
    }
    # Minimum confidence to place a trade (low = trades more, generates learning data)
    MIN_TRADE_CONFIDENCE = {
        "momentum": 0.01,       # trades almost everything (aggressive learner)
        "mean_reversion": 0.06, # slightly selective
        "mean_reversion_sl": 0.06,
        "mean_reversion_tp": 0.06,
        "sentiment": 0.03,      # moderate
        "hybrid": 0.05,         # moderate-selective
        "orderflow": 0.05,
    }

    def __init__(self, name, strategy_type, params, generation=0, lineage=None):
        self.name = name
        self.strategy_type = strategy_type
        self.strategy_params = params
        self.generation = generation
        self.lineage = lineage or name
        self._paused = False
        self._pause_reason = None

    @abstractmethod
    def analyze(self, market: dict, signals: dict) -> dict:
        """Analyze market + signals and return a trade signal.

        Returns:
            {
                "action": "buy" | "sell" | "hold",
                "side": "yes" | "no",
                "confidence": 0.0-1.0,
                "reasoning": "why this trade",
                "suggested_amount": float,
            }
        """
        pass

    def make_decision(self, market: dict, signals: dict) -> dict:
        market_price = market.get("current_price", 0.5)
        try:
            market_price = float(market_price)
        except (TypeError, ValueError):
            market_price = 0.5
        market_price = max(0.01, min(0.99, market_price))

        prices = signals.get("prices", []) or []
        btc_latest = signals.get("latest", 0) or 0

        price_momentum = 0.0
        if len(prices) >= 2 and prices[-1] > 0:
            price_momentum = (prices[-1] - prices[-2]) / prices[-2]
        elif btc_latest > 0 and len(prices) >= 1 and prices[-1] > 0:
            price_momentum = (btc_latest - prices[-1]) / prices[-1]

        momentum_signal = max(-0.20, min(0.20, float(price_momentum) * 35))

        vol = 0.0
        if len(prices) >= 6:
            rets = []
            for i in range(max(1, len(prices) - 16), len(prices)):
                p0 = prices[i - 1]
                p1 = prices[i]
                if p0 and p0 > 0:
                    rets.append((p1 - p0) / p0)
            if len(rets) >= 5:
                m = sum(rets) / len(rets)
                var = sum((r - m) ** 2 for r in rets) / max(1, (len(rets) - 1))
                vol = math.sqrt(max(0.0, var))

        raw_signal = self.analyze(market, signals)
        strat = 0.0
        if raw_signal.get("action") != "hold":
            side = raw_signal.get("side")
            conf = raw_signal.get("confidence", 0.0) or 0.0
            strat = (1.0 if side == "yes" else -1.0) * float(conf)

        s = signals.get("sentiment") or {}
        sent = float(s.get("score", 0.5) or 0.5) - 0.5

        of = signals.get("orderflow") or {}
        of_prob = of.get("current_probability", market_price)
        try:
            of_prob = float(of_prob)
        except (TypeError, ValueError):
            of_prob = market_price
        of_delta = max(-0.25, min(0.25, of_prob - market_price))

        of_vol_24h = of.get("volume_24h", 0) or 0
        try:
            of_vol_24h = float(of_vol_24h)
        except (TypeError, ValueError):
            of_vol_24h = 0.0
        of_vol = math.log1p(max(0.0, of_vol_24h)) / 10.0

        tte = of.get("time_to_resolution", 0) or 0
        try:
            tte = float(tte)
        except (TypeError, ValueError):
            tte = 0.0
        tte = max(0.0, min(900.0, tte))
        tte_n = tte / 300.0

        stale = 1.0 if signals.get("stale") else 0.0

        x = {
            "mom": momentum_signal,
            "vol": vol,
            "tte": tte_n,
            "strat": strat,
            "sent": sent,
            "of_delta": of_delta,
            "of_vol": of_vol,
            "stale": stale,
        }

        p_yes_raw = edge_model.predict_yes_probability(self.name, market_price, x)

        adv_edge = None
        try:
            from advanced_edge_models import compute_advanced_edge

            adv_edge = compute_advanced_edge(self.name, market, signals, p_yes_raw)
            p_yes = float(adv_edge.get("p_yes", p_yes_raw) or p_yes_raw)
        except Exception:
            p_yes = p_yes_raw

        entry_buffer = config.get_entry_price_buffer()
        fee_rate = config.get_fee_rate()

        p_buy_yes = max(0.01, min(0.99, market_price + entry_buffer))
        p_buy_no = max(0.01, min(0.99, (1.0 - market_price) + entry_buffer))
        p_eff_yes = max(0.01, min(0.99, p_buy_yes * (1.0 + fee_rate)))
        p_eff_no = max(0.01, min(0.99, p_buy_no * (1.0 + fee_rate)))

        ev_yes = (p_yes - p_eff_yes) / p_eff_yes
        ev_no = ((1.0 - p_yes) - p_eff_no) / p_eff_no

        side = "yes" if ev_yes >= ev_no else "no"
        best_ev = ev_yes if side == "yes" else ev_no

        min_ev = getattr(config, "MIN_EXPECTED_VALUE", 0.0)
        if best_ev < float(min_ev):
            features = {
                "x": x,
                "market_price": market_price,
                "p_yes": p_yes,
                "p_entry_yes": p_eff_yes,
                "p_entry_no": p_eff_no,
            }
            if adv_edge is not None:
                features["advanced_edge"] = adv_edge

            return {
                "action": "skip",
                "side": side,
                "confidence": min(0.95, abs(p_yes - market_price) * 2.5),
                "reasoning": f"No edge after costs: p_yes={p_yes:.3f} mkt={market_price:.3f} ev_yes={ev_yes:.2%} ev_no={ev_no:.2%}",
                "suggested_amount": 0,
                "features": features,
            }

        max_pos = config.get_max_position()
        k_frac = getattr(config, "KELLY_FRACTION", 0.5)
        k_yes = (p_yes - p_eff_yes) / max(1e-6, (1.0 - p_eff_yes))
        k_no = ((1.0 - p_yes) - p_eff_no) / max(1e-6, (1.0 - p_eff_no))
        k = k_yes if side == "yes" else k_no
        k = max(0.0, min(0.25, k))
        amount = max_pos * k * k_frac

        confidence = min(0.95, abs(p_yes - market_price) * 2.5)
        reasoning = (
            f"p_yes={p_yes:.3f} mkt={market_price:.3f} "
            f"ev_yes={ev_yes:.2%} ev_no={ev_no:.2%} "
            f"mom={momentum_signal:+.3f} vol={vol:.4f} tte={tte:.0f}s strat={strat:+.3f}"
        )

        features = {
            "x": x,
            "market_price": market_price,
            "p_yes": p_yes,
            "p_entry_yes": p_eff_yes,
            "p_entry_no": p_eff_no,
        }
        if adv_edge is not None:
            features["advanced_edge"] = adv_edge

        return {
            "action": "buy",
            "side": side,
            "confidence": confidence,
            "reasoning": reasoning,
            "suggested_amount": float(amount),
            "features": features,
        }

    def execute(self, signal: dict, market: dict) -> dict:
        """Place a trade via Simmer SDK based on the signal."""
        mode = config.get_current_mode()
        try:
            reset_key = f"unpause:{self.name}:{mode}"
            if str(db.get_arena_state(reset_key, "0")) == "1":
                self._paused = False
                self._pause_reason = None
                db.set_arena_state(reset_key, "0")
        except Exception:
            pass

        if self._paused:
            reason_msg = f" ({self._pause_reason})" if self._pause_reason else ""
            logger.info(f"[{self.name}] Paused{reason_msg}, skipping trade")
            return {"success": False, "reason": "bot_paused"}
        venue = config.get_venue()
        max_pos = config.get_max_position()


        max_trades_hr = getattr(config, "MAX_TRADES_PER_HOUR_PER_BOT", None)
        if max_trades_hr is not None:
            try:
                with db.get_conn() as conn:
                    row = conn.execute(
                        "SELECT COUNT(*) as c FROM trades WHERE bot_name=? AND mode=? AND created_at >= datetime('now', '-1 hour')",
                        (self.name, mode),
                    ).fetchone()
                if row and int(dict(row)["c"]) >= int(max_trades_hr):
                    return {"success": False, "reason": "trade_rate_limit"}
            except Exception:
                pass

        # Check risk limits - NOVO SISTEMA CENTRALIZADO
        amount = min(signal.get("suggested_amount", max_pos * 0.5), max_pos)
        
        # Usar o RiskManager centralizado
        allowed, reason = risk_manager.can_place_trade(
            bot_name=self.name,
            amount=amount,
            market=market
        )
        
        if not allowed:
            # Se for daily_loss_per_bot, pausar o bot
            if reason == "daily_loss_per_bot":
                self._paused = True
                self._pause_reason = "daily_loss_limit"
            return {"success": False, "reason": reason}

        try:
            if mode == "live":
                return self._execute_live(signal, market, amount, mode)
            else:
                return self._execute_paper(signal, market, amount, venue, mode)

        except Exception as e:
            logger.error(f"[{self.name}] Trade exception: {e}")
            # Send Telegram notification for trade error
            telegram = get_telegram_notifier()
            if telegram:
                telegram.notify_error(self.name, f"Trade exception: {str(e)}")
            return {"success": False, "reason": str(e)}

    def get_performance(self, hours=12) -> dict:
        """Get bot performance stats."""
        perf = db.get_bot_performance(self.name, hours)
        perf["name"] = self.name
        perf["strategy_type"] = self.strategy_type
        perf["generation"] = self.generation
        perf["paused"] = self._paused
        return perf

    def export_params(self) -> dict:
        return {
            "name": self.name,
            "strategy_type": self.strategy_type,
            "generation": self.generation,
            "lineage": self.lineage,
            "params": copy.deepcopy(self.strategy_params),
        }

    def mutate(self, winning_params: dict, mutation_rate: float = None) -> dict:
        """Create mutated params from winning bot's params."""
        rate = mutation_rate or config.MUTATION_RATE
        new_params = copy.deepcopy(winning_params)

        numeric_keys = [k for k, v in new_params.items() if isinstance(v, (int, float))]
        num_mutations = min(random.randint(2, 3), len(numeric_keys))
        keys_to_mutate = random.sample(numeric_keys, num_mutations) if numeric_keys else []

        for key in keys_to_mutate:
            val = new_params[key]
            delta = val * random.uniform(-rate, rate)
            new_val = val + delta
            if isinstance(val, int):
                new_params[key] = max(1, int(new_val))
            else:
                new_params[key] = max(0.01, round(new_val, 4))

        return new_params

    def reset_daily(self):
        """Reset daily pause state."""
        was_paused = self._paused  # Check if bot was paused before
        self._paused = False
        self._pause_reason = None
        
        # Send Telegram notification if bot was resumed
        if was_paused:
            telegram = get_telegram_notifier()
            if telegram:
                telegram.notify_bot_resumed(self.name)

    def _execute_paper(self, signal, market, amount, venue, mode):
        """Execute via Simmer (paper trading) with professional-style TWAP slicing and EV filter."""
        import requests
        api_key = self._load_api_key()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Expected value threshold after costs (paper approximates costs conservatively)
        expected_value = abs(signal.get("confidence", 0.5) - 0.5) * 2
        min_ev = float(getattr(config, "EXECUTION_MIN_EV_AFTER_COSTS", 0.045))
        if expected_value < min_ev:
            return {"success": False, "reason": "ev_below_min_after_costs"}

        # TWAP slicing for paper mode to emulate professional execution
        slices = int(getattr(config, "EXECUTION_TWAP_SLICES", 4))
        interval = int(getattr(config, "EXECUTION_TWAP_INTERVAL_SECONDS", 30))
        slice_amount = max(0.01, float(amount) / max(1, slices))

        total_shares = 0.0
        slice_results = []
        for i in range(slices):
            payload = {
                "market_id": market.get("id") or market.get("market_id"),
                "side": signal["side"],
                "amount": slice_amount,
                "venue": venue,
                "source": f"arena:{self.name}",
                "reasoning": f"{signal.get('reasoning', '')} | TWAP slice {i+1}/{slices}",
            }

            resp = requests.post(
                f"{config.SIMMER_BASE_URL}/api/sdk/trade",
                headers=headers, json=payload, timeout=30
            )

            if resp.status_code in (200, 201):
                result = resp.json()
                shares = float(result.get("shares_bought") or 0.0)
                total_shares += shares
                slice_results.append(result)
                db.log_trade(
                    bot_name=self.name,
                    market_id=market.get("id") or market.get("market_id"),
                    market_question=market.get("question"),
                    side=signal["side"],
                    amount=slice_amount,
                    venue=venue,
                    mode=mode,
                    confidence=signal["confidence"],
                    reasoning=payload["reasoning"],
                    trade_id=result.get("trade_id"),
                    shares_bought=shares,
                    trade_features=signal.get("features"),
                )
                amt_s = f"{slice_amount:.4f}" if float(slice_amount) < 0.01 else f"{slice_amount:.2f}"
                logger.info(f"[{self.name}] Paper TWAP slice {i+1}/{slices}: {signal['side']} ${amt_s} on {market.get('question', '')[:50]}")
            else:
                logger.error(f"[{self.name}] Paper slice {i+1}/{slices} failed: {resp.status_code} {resp.text[:200]}")
                return {"success": False, "reason": f"api_error_{resp.status_code}"}

            # Wait between slices except final
            if i < slices - 1:
                time.sleep(interval)

        return {"success": True, "trade_id": slice_results[-1].get("trade_id") if slice_results else None, "total_shares": total_shares}

    def _execute_live(self, signal, market, amount, mode):
        """Execute directly on Polymarket CLOB (live trading) with professional execution engine."""
        import polymarket_client
        from execution_engine import execute_professional_trade, OrderType

        side = signal["side"].lower()
        if side == "yes":
            token_id = market.get("polymarket_token_id")
        else:
            token_id = market.get("polymarket_no_token_id")

        if not token_id:
            logger.error(f"[{self.name}] No token ID for side={side} on {market.get('question', '')[:50]}")
            return {"success": False, "reason": "missing_token_id"}

        # Get market data for professional execution
        market_data = polymarket_client.get_market_info(token_id)
        if not market_data:
            logger.error(f"[{self.name}] Failed to get market data for {market.get('question', '')[:50]}")
            return {"success": False, "reason": "no_market_data"}

        # Calculate expected value from signal
        expected_value = abs(signal.get("confidence", 0.5) - 0.5) * 2  # Convert confidence to EV
        
        # Convert amount to shares (approximate)
        current_price = market_data.get("best_ask", 0.5) if side == "yes" else market_data.get("best_bid", 0.5)
        size = amount / max(0.01, current_price)

        # Execute professional trade with intelligent order management
        result = execute_professional_trade(
            market_data=market_data,
            side=side,
            size=size,
            token_id=token_id,
            expected_value=expected_value,
            client_func=polymarket_client.place_market_order
        )

        if result.get("success"):
            # Aggregate results from multiple executions
            total_executed = result.get("total_executed", 0)
            total_cost = result.get("total_cost", 0)
            strategy = result.get("strategy", "UNKNOWN")
            
            db.log_trade(
                bot_name=self.name,
                market_id=market.get("id") or market.get("market_id"),
                market_question=market.get("question"),
                side=signal["side"],
                amount=amount,
                venue="polymarket",
                mode=mode,
                confidence=signal["confidence"],
                reasoning=f"{signal.get('reasoning', '')} | Strategy: {strategy} | Cost: ${total_cost:.3f}",
                trade_id=f"PRO_{int(time.time())}",  # Generate professional trade ID
                shares_bought=total_executed,
            )
            logger.info(f"[{self.name}] PROFESSIONAL trade: {signal['side']} ${amount} executed with {strategy} strategy, cost: ${total_cost:.3f} on {market.get('question', '')[:50]}")
            
        else:
            logger.error(f"[{self.name}] PROFESSIONAL trade failed: {result.get('error')}")
            # Send Telegram notification for failed trade
            try:
                notifier = get_telegram_notifier()
                if notifier and notifier.enabled:
                    notifier.send_trade_failed(
                        bot_name=self.name,
                        market=market.get("question", "Unknown"),
                        side=signal["side"],
                        amount=amount,
                        error=result.get("error", "Unknown error"),
                        mode=mode,
                    )
            except Exception as e:
                logger.warning(f"Failed to send Telegram notification: {e}")
            
        return result

    def _load_api_key(self):
        import json as _json
        # Try per-bot key first, then fall back to default
        try:
            with open(config.SIMMER_BOT_KEYS_PATH) as f:
                bot_keys = _json.load(f)
            if self.name in bot_keys:
                return bot_keys[self.name]
            # Check by slot assignment (for evolved bots inheriting a slot)
            if hasattr(self, '_api_key_slot') and self._api_key_slot in bot_keys:
                return bot_keys[self._api_key_slot]
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        # Fallback: default key
        with open(config.SIMMER_API_KEY_PATH) as f:
            return _json.load(f).get("api_key")
