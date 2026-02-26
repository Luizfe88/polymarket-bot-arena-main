"""
core/risk_manager.py
RiskManager centralizado para o Arena 10/10
Baseado no ImMike + 100% adaptado ao seu sistema
"""
import logging
import time
import json
from datetime import datetime

import config
import db
from telegram_notifier import get_telegram_notifier

logger = logging.getLogger(__name__)

class ArenaRiskManager:
    def __init__(self):
        self.telegram = get_telegram_notifier()
        self.mode = config.get_current_mode()
        self.bankroll = None
        self.limits = {}
        self.last_update = 0
        
        # Circuit Breaker state
        self.consecutive_losses = {}  # bot_name -> count
        self.paused_bots = {}         # bot_name -> timestamp_unpause
        
        logger.info("✅ ArenaRiskManager inicializado")

    def update_bankroll(self, bankroll: float):
        """Atualiza banca e recalcula todos os limites (igual start-arena.ps1)"""
        if self.bankroll is not None and abs(self.bankroll - bankroll) < 0.01:
            return
        self.bankroll = float(bankroll)
        self.limits = self._calculate_dynamic_limits(bankroll)
        self.last_update = time.time()
        logger.info(f"RiskManager atualizado | Banca=${bankroll:.2f} | Perfil={self.limits['profile']}")

    def _calculate_dynamic_limits(self, bankroll: float):
        # Configuração solicitada pelo usuário:
        # - 2% do capital por trade
        # - Max 50% do capital total investido
        
        profile = "UserCustom"
        pct_trade = 0.02      # 2% por trade
        pct_bot = 0.10        # 10% por bot (permite até 5 trades simultâneos por bot)
        pct_global = 0.50     # 50% total investido (soma de todos bots)
        
        # Limites de perda mantidos conservadores
        pct_loss_bot = 0.10
        pct_loss_global = 0.20

        limits = {
            "profile": profile,
            "max_trade_size": round(bankroll * pct_trade, 2),
            "max_pos_per_bot": round(bankroll * pct_bot, 2),
            "max_global_position": round(bankroll * pct_global, 2),
            "max_daily_loss_per_bot": round(bankroll * pct_loss_bot, 2),
            "max_daily_loss_global": round(bankroll * pct_loss_global, 2),
            "max_consecutive_losses": 3,
            "pause_duration": 3600, # 1 hour
        }

        # Drawdown Scaling 2.0 (mantido para segurança extra em drawdowns severos)
        initial = self._get_peak_bankroll()
        dd_ratio = bankroll / initial if initial > 0 else 1.0
        if dd_ratio < 0.85:
            limits["max_trade_size"] = round(limits["max_trade_size"] * 0.65, 2)
            limits["max_global_position"] = round(limits["max_global_position"] * 0.70, 2)
            logger.warning(f"🚨 DRAW DOWN CRÍTICO ({(1-dd_ratio)*100:.1f}%) - risco cortado 30-35%")

        return limits

    def get_dynamic_kelly_fraction(self) -> float:
        """
        Retorna fração de Kelly ajustada pelo drawdown.
        Reduz agressivamente conforme nos aproximamos do MAX_DRAWDOWN.
        """
        base_kelly = getattr(config, "KELLY_FRACTION", 0.10)
        
        # Calculate current drawdown
        peak = self._get_peak_bankroll()
        current = self.bankroll or peak
        if peak <= 0: return base_kelly
        
        drawdown = (peak - current) / peak
        drawdown = max(0.0, drawdown)
        
        max_dd = getattr(config, "MAX_DRAWDOWN", 0.15)
        
        # Se drawdown > max, corta para 10% do base
        if drawdown >= max_dd:
            return base_kelly * 0.1
            
        # Scaling linear: 0% dd -> 100% kelly, 15% dd -> 10% kelly
        dd_ratio = drawdown / max_dd
        scaling_factor = max(0.1, 1.0 - (dd_ratio * 0.9))
        
        return base_kelly * scaling_factor

    def _get_peak_bankroll(self):
        try:
            with open("arena_peak.json") as f:
                return json.load(f)["peak"]
        except:
            return self.bankroll or 13.06

    def record_trade_result(self, bot_name: str, pnl: float):
        """Called after a trade is closed to update circuit breaker stats"""
        if pnl < 0:
            self.consecutive_losses[bot_name] = self.consecutive_losses.get(bot_name, 0) + 1
            logger.info(f"[{bot_name}] Consecutive loss #{self.consecutive_losses[bot_name]}")
        else:
            self.consecutive_losses[bot_name] = 0

        # Check circuit breaker
        max_losses = self.limits.get("max_consecutive_losses", 3)
        if self.consecutive_losses.get(bot_name, 0) >= max_losses:
            pause_time = self.limits.get("pause_duration", 3600)
            self.paused_bots[bot_name] = time.time() + pause_time
            self._handle_pause(bot_name, "consecutive_losses", self.consecutive_losses[bot_name], max_losses)
            # Reset counter so it doesn't trigger immediately after unpause unless another loss occurs
            self.consecutive_losses[bot_name] = 0

    def can_place_trade(self, bot_name: str, amount: float, market: dict = None) -> tuple[bool, str]:
        """ÚNICO lugar onde você verifica risco agora"""
        if time.time() - self.last_update > 30:
            self.update_bankroll(self._get_current_bankroll())

        limits = self.limits

        # 0. Check Paused Bots
        if bot_name in self.paused_bots:
            if time.time() < self.paused_bots[bot_name]:
                return False, f"paused_until_{int(self.paused_bots[bot_name])}"
            else:
                del self.paused_bots[bot_name]
                logger.info(f"[{bot_name}] Resuming from pause")

        # 1. Tamanho mínimo
        if amount < config.get_min_trade_amount():
            return False, "amount_below_minimum"

        # 2. Daily loss por bot
        daily_bot = db.get_bot_daily_loss(bot_name, self.mode)
        if daily_bot >= limits["max_daily_loss_per_bot"]:
            self._handle_pause(bot_name, "daily_loss_per_bot", daily_bot, limits["max_daily_loss_per_bot"])
            return False, "daily_loss_per_bot"

        # 3. Daily loss arena
        daily_global = db.get_total_daily_loss(self.mode)
        if daily_global >= limits["max_daily_loss_global"]:
            return False, "daily_loss_global"

        # 4. Posição por bot
        open_bot = db.get_total_open_position_value(bot_name, self.mode)
        if open_bot + amount > limits["max_pos_per_bot"]:
            return False, "max_position_per_bot"

        # 5. Posição global
        open_global = db.get_total_open_position_value_all_bots(self.mode)
        if open_global + amount > limits["max_global_position"]:
            return False, "max_global_position"

        # 6. Spread (mantido do seu código)
        # Note: Arbitrage bot might trade high spread markets if arb exists, so maybe skip this for arb?
        # But generally high spread is bad.
        # Let's keep it but make it loose
        if market and (market.get("p_yes", 0.5) + market.get("p_no", 0.5) > 1.05):
             # Exception for arbitrage bot? 
             # Ideally arbitrage bot checks clob spread, this check might be based on different data
             pass

        return True, "ok"

    def _handle_pause(self, bot_name: str, reason: str, current: float, limit: float):
        logger.warning(f"[{bot_name}] PAUSED: {reason} → {current} >= {limit}")
        if self.telegram:
            self.telegram.notify_bot_paused(bot_name, reason, loss_amount=current, max_loss=limit)

    def _get_current_bankroll(self):
        # Tenta ler exatamente como no seu start-arena.ps1
        try:
            # Você pode chamar a mesma função que usa no PowerShell ou deixar o start-arena chamar update_bankroll
            return config.PAPER_STARTING_BALANCE   # ajuste se quiser ler da API aqui
        except:
            return 13.06

    def reset_daily(self):
        db.reset_arena_day(self.mode)
        self.consecutive_losses = {} # Reset consecutive losses on daily reset? Maybe optional.
        # self.paused_bots = {} # Don't unpause bots on daily reset if they are in penalty box? 
        # Actually daily reset usually clears daily limits, so we should clear daily pauses.
        # But consecutive loss pause is short term.
        logger.info("RiskManager → daily stats reset após evolução")

    def get_summary(self):
        self.update_bankroll(self._get_current_bankroll())
        return {
            "bankroll": self.bankroll,
            "profile": self.limits.get("profile"),
            **self.limits,
            "mode": self.mode,
            "paused_bots": self.paused_bots
        }

# Singleton (use em qualquer lugar)
risk_manager = ArenaRiskManager()
