from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import logging

from .tracker import WalletTracker
from .copier import TradeCopier

import config
import db
from llm_sentiment_engine import AdvancedLLMSentimentEngine
from core.risk_manager import risk_manager


logger = logging.getLogger(__name__)


@dataclass
class WhaleMetrics:
    address: str
    label: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_volume: float
    total_pnl: float


@dataclass
class LLMReviewResult:
    approved: bool
    confidence: float
    reasoning: str


class AdvancedWhaleCopyTrader:
    def __init__(
        self,
        tracker: Optional[WalletTracker] = None,
        min_win_rate: float = 0.7,
        min_volume_usd: float = 50000.0,
        lookback_days: int = 30,
        max_whales: int = 50,
        llm_confidence_threshold: float = 0.6,
    ):
        self.tracker = tracker or WalletTracker()
        self.copier = TradeCopier(self.tracker)
        self.min_win_rate = min_win_rate
        self.min_volume_usd = min_volume_usd
        self.lookback_days = lookback_days
        self.max_whales = max_whales
        self.llm_engine = AdvancedLLMSentimentEngine(confidence_threshold=llm_confidence_threshold)

    def _compute_wallet_metrics(self) -> Dict[str, WhaleMetrics]:
        since = datetime.utcnow() - timedelta(days=self.lookback_days)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")

        with db.get_conn() as conn:
            rows = conn.execute(
                """
                SELECT wallet_address,
                       COUNT(*) AS trades,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN pnl <= 0 AND outcome IS NOT NULL THEN 1 ELSE 0 END) AS losses,
                       COALESCE(SUM(amount), 0) AS volume,
                       COALESCE(SUM(pnl), 0) AS total_pnl
                FROM copytrading_trades
                WHERE created_at >= ?
                GROUP BY wallet_address
                """,
                (since_str,),
            ).fetchall()

            metrics: Dict[str, WhaleMetrics] = {}

            labels = {
                r["address"]: r["label"] or r["address"][:12]
                for r in conn.execute(
                    "SELECT address, label FROM copytrading_wallets WHERE active=1"
                ).fetchall()
            }

            for r in rows:
                wallet = r["wallet_address"]
                trades = r["trades"] or 0
                wins = r["wins"] or 0
                losses = r["losses"] or 0
                total = wins + losses
                win_rate = wins / total if total > 0 else 0.0
                volume = float(r["volume"] or 0.0)
                pnl = float(r["total_pnl"] or 0.0)

                metrics[wallet] = WhaleMetrics(
                    address=wallet,
                    label=labels.get(wallet, wallet[:12]),
                    total_trades=trades,
                    wins=wins,
                    losses=losses,
                    win_rate=win_rate,
                    total_volume=volume,
                    total_pnl=pnl,
                )

            return metrics

    def _select_top_whales(self) -> List[str]:
        metrics = self._compute_wallet_metrics()
        qualified: List[WhaleMetrics] = []

        for m in metrics.values():
            if m.total_trades < 10:
                continue
            if m.win_rate < self.min_win_rate:
                continue
            if m.total_volume < self.min_volume_usd:
                continue
            qualified.append(m)

        if not qualified:
            tracked = self.tracker.get_tracked()
            return [w["address"] for w in tracked][: self.max_whales]

        qualified.sort(key=lambda x: (x.win_rate, x.total_pnl), reverse=True)
        top = qualified[: self.max_whales]
        return [m.address for m in top]

    def _review_trade_with_llm(
        self,
        wallet_address: str,
        market_question: str,
        side: str,
        amount: float,
    ) -> LLMReviewResult:
        text = (
            f"Wallet {wallet_address[:12]} opened a position {side.upper()} "
            f"with size ${amount:.2f} in the Polymarket market: {market_question}"
        )

        signal = self.llm_engine.analyze_text_sentiment(
            text=text,
            source="whale_alert",
            market_context={"side": side, "amount": amount},
        )

        approved = signal.sentiment_score >= 0 and signal.confidence >= self.llm_engine.confidence_threshold
        reasoning = (
            f"score={signal.sentiment_score:.3f}, conf={signal.confidence:.3f}, "
            f"keywords={','.join(signal.keywords[:5])}"
        )

        return LLMReviewResult(
            approved=approved,
            confidence=signal.confidence,
            reasoning=reasoning,
        )

    def _log_copy_trade(
        self,
        wallet_address: str,
        market_id: str,
        side: str,
        amount: float,
        our_trade_id: Optional[str],
        outcome: Optional[str] = None,
        pnl: Optional[float] = None,
    ) -> None:
        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO copytrading_trades
                    (wallet_address, market_id, side, amount, our_trade_id, outcome, pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    wallet_address,
                    market_id,
                    side,
                    amount,
                    our_trade_id,
                    outcome,
                    pnl,
                ),
            )

    def _compute_position_size_cap(self, bot_name: str) -> float:
        limits = risk_manager.limits or {}
        max_trade_size = limits.get("max_trade_size") or config.get_max_position()
        kelly_fraction = config.KELLY_FRACTION
        return max_trade_size * kelly_fraction

    def _filter_and_log_trades(self, raw_trades: List[Dict]) -> List[Dict]:
        filtered: List[Dict] = []

        cap = self._compute_position_size_cap("whale_copy")

        for t in raw_trades:
            wallet = t.get("wallet", "")
            market_question = t.get("market_question", "")
            side = t.get("side", "")
            amount = float(t.get("amount", 0.0))
            market_id = t.get("market_id", "")
            trade_id = t.get("trade_id")

            if not wallet or not market_id or amount <= 0:
                continue

            ok, reason = risk_manager.can_place_trade("whale_copy", amount)
            if not ok:
                logger.info(f"Whale copy trade blocked by risk manager: {reason}")
                continue

            if amount > cap:
                scale = cap / amount
                amount = cap
                t["amount"] = amount
                t["scaled_from"] = scale

            review = self._review_trade_with_llm(wallet, market_question, side, amount)
            if not review.approved:
                logger.info(
                    f"LLM rejected whale trade {market_id} from {wallet[:12]}: {review.reasoning}"
                )
                continue

            self._log_copy_trade(
                wallet_address=wallet,
                market_id=market_id,
                side=side,
                amount=amount,
                our_trade_id=trade_id,
            )

            t["llm_confidence"] = review.confidence
            t["llm_reasoning"] = review.reasoning
            filtered.append(t)

        return filtered

    def run_copy_cycle(self, api_key: str) -> Tuple[List[Dict], List[Dict]]:
        if not config.COPYTRADING_ENABLED:
            logger.info("Advanced whale copy trading disabled by config")
            return [], []

        risk_manager.update_bankroll(risk_manager._get_current_bankroll())

        whales = self._select_top_whales()
        if not whales:
            logger.info("No whales available for copy trading")
            return [], []

        raw_trades = self.copier.execute_copy(api_key=api_key, wallets=whales)
        if not raw_trades:
            return [], []

        filtered_trades = self._filter_and_log_trades(raw_trades)
        logger.info(
            f"Advanced whale copier approved {len(filtered_trades)}/{len(raw_trades)} trades"
        )
        return raw_trades, filtered_trades

