"""
Protocol Zero — Real-Time Performance Tracker
================================================
Tracks live portfolio performance with institutional-grade metrics.

Metrics Computed:
  • Sharpe Ratio         — risk-adjusted return (annualized)
  • Max Drawdown         — largest peak-to-trough decline
  • Sortino Ratio        — downside-risk adjusted return
  • Calmar Ratio         — return / max drawdown
  • Win Rate             — percentage of profitable trades
  • Profit Factor        — gross profit / gross loss
  • Equity Curve         — running portfolio value over time
  • Rolling Volatility   — 20-period rolling std of returns

Usage:
    from performance_tracker import PerformanceTracker

    tracker = PerformanceTracker(initial_capital=10_000.0)
    tracker.record_trade("BUY", "ETH", 200.0, pnl=15.50)
    report = tracker.get_report()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("protocol_zero.performance")

# Persistence file for cross-session tracking
_PERF_FILE = Path(__file__).resolve().parent / "performance_history.json"


@dataclass
class TradeRecord:
    """Single trade record for performance tracking."""
    timestamp: float
    action: str
    asset: str
    amount_usd: float
    pnl_usd: float
    confidence: float
    risk_score: int
    market_regime: str
    entry_price: float = 0.0
    exit_price: float = 0.0
    duration_seconds: float = 0.0


class PerformanceTracker:
    """
    Real-time portfolio performance tracker with institutional metrics.

    Tracks equity curve, calculates Sharpe/Sortino/Calmar ratios,
    max drawdown, win rate, profit factor, and rolling volatility.
    """

    def __init__(self, initial_capital: float = 10_000.0) -> None:
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades: list[TradeRecord] = []
        self.equity_curve: list[dict] = [
            {
                "timestamp": time.time(),
                "equity": initial_capital,
                "pnl": 0.0,
            }
        ]
        self.peak_equity = initial_capital
        self.max_drawdown_usd = 0.0
        self.max_drawdown_pct = 0.0
        self._session_start = time.time()
        self._load_history()

    # ────────────────────────────────────────────────────────
    #  Trade Recording
    # ────────────────────────────────────────────────────────

    def record_trade(
        self,
        action: str,
        asset: str,
        amount_usd: float,
        pnl_usd: float = 0.0,
        confidence: float = 0.0,
        risk_score: int = 5,
        market_regime: str = "UNCERTAIN",
        entry_price: float = 0.0,
        exit_price: float = 0.0,
    ) -> TradeRecord:
        """Record a completed trade and update equity curve."""
        trade = TradeRecord(
            timestamp=time.time(),
            action=action,
            asset=asset,
            amount_usd=amount_usd,
            pnl_usd=pnl_usd,
            confidence=confidence,
            risk_score=risk_score,
            market_regime=market_regime,
            entry_price=entry_price,
            exit_price=exit_price,
        )
        self.trades.append(trade)
        self.current_capital += pnl_usd

        # Update equity curve
        self.equity_curve.append({
            "timestamp": trade.timestamp,
            "equity": self.current_capital,
            "pnl": pnl_usd,
        })

        # Update peak and drawdown
        if self.current_capital > self.peak_equity:
            self.peak_equity = self.current_capital
        drawdown_usd = self.peak_equity - self.current_capital
        drawdown_pct = (drawdown_usd / self.peak_equity * 100) if self.peak_equity > 0 else 0
        if drawdown_usd > self.max_drawdown_usd:
            self.max_drawdown_usd = drawdown_usd
            self.max_drawdown_pct = drawdown_pct

        logger.info(
            "📊 Trade recorded: %s %s $%.2f PnL=$%.2f | Equity=$%.2f",
            action, asset, amount_usd, pnl_usd, self.current_capital,
        )
        self._save_history()
        return trade

    # ────────────────────────────────────────────────────────
    #  Core Metrics
    # ────────────────────────────────────────────────────────

    @property
    def returns(self) -> np.ndarray:
        """Array of per-trade returns as fractions."""
        if not self.trades:
            return np.array([])
        return np.array([
            t.pnl_usd / max(t.amount_usd, 1.0) for t in self.trades
            if t.action in ("BUY", "SELL")
        ])

    @property
    def pnl_series(self) -> np.ndarray:
        """Array of per-trade PnL in USD."""
        return np.array([
            t.pnl_usd for t in self.trades
            if t.action in ("BUY", "SELL")
        ])

    def sharpe_ratio(self, risk_free_rate: float = 0.05, periods_per_year: int = 365 * 24) -> float:
        """
        Annualized Sharpe Ratio.
        
        Uses hourly trading periods by default (crypto is 24/7).
        """
        rets = self.returns
        if len(rets) < 2:
            return 0.0
        excess_returns = rets - (risk_free_rate / periods_per_year)
        std = np.std(excess_returns, ddof=1)
        if std == 0:
            return 0.0
        return float(np.mean(excess_returns) / std * np.sqrt(periods_per_year))

    def sortino_ratio(self, risk_free_rate: float = 0.05, periods_per_year: int = 365 * 24) -> float:
        """Sortino Ratio — only penalizes downside volatility."""
        rets = self.returns
        if len(rets) < 2:
            return 0.0
        excess_returns = rets - (risk_free_rate / periods_per_year)
        downside = rets[rets < 0]
        if len(downside) == 0:
            return float("inf") if np.mean(excess_returns) > 0 else 0.0
        downside_std = np.std(downside, ddof=1)
        if downside_std == 0:
            return 0.0
        return float(np.mean(excess_returns) / downside_std * np.sqrt(periods_per_year))

    def calmar_ratio(self) -> float:
        """Calmar Ratio — annualized return / max drawdown."""
        if self.max_drawdown_pct == 0 or not self.trades:
            return 0.0
        total_return_pct = ((self.current_capital - self.initial_capital)
                            / self.initial_capital * 100)
        elapsed_years = max((time.time() - self._session_start) / (365.25 * 86400), 1 / 365.25)
        annualized_return = total_return_pct / elapsed_years
        return annualized_return / self.max_drawdown_pct

    def win_rate(self) -> float:
        """Percentage of profitable trades."""
        executed = [t for t in self.trades if t.action in ("BUY", "SELL")]
        if not executed:
            return 0.0
        wins = sum(1 for t in executed if t.pnl_usd > 0)
        return wins / len(executed) * 100

    def profit_factor(self) -> float:
        """Gross profit / gross loss."""
        pnls = self.pnl_series
        if len(pnls) == 0:
            return 0.0
        gross_profit = float(np.sum(pnls[pnls > 0]))
        gross_loss = float(np.abs(np.sum(pnls[pnls < 0])))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def rolling_volatility(self, window: int = 20) -> float:
        """Rolling volatility of returns (std over last N trades)."""
        rets = self.returns
        if len(rets) < window:
            if len(rets) >= 2:
                return float(np.std(rets, ddof=1))
            return 0.0
        return float(np.std(rets[-window:], ddof=1))

    def total_pnl(self) -> float:
        """Total PnL in USD."""
        return self.current_capital - self.initial_capital

    def total_return_pct(self) -> float:
        """Total return as percentage."""
        if self.initial_capital == 0:
            return 0.0
        return (self.current_capital - self.initial_capital) / self.initial_capital * 100

    def average_trade_pnl(self) -> float:
        """Average PnL per trade."""
        pnls = self.pnl_series
        if len(pnls) == 0:
            return 0.0
        return float(np.mean(pnls))

    def best_trade(self) -> float:
        """Best single trade PnL."""
        pnls = self.pnl_series
        return float(np.max(pnls)) if len(pnls) > 0 else 0.0

    def worst_trade(self) -> float:
        """Worst single trade PnL."""
        pnls = self.pnl_series
        return float(np.min(pnls)) if len(pnls) > 0 else 0.0

    def trades_by_regime(self) -> dict[str, dict]:
        """Performance breakdown by market regime."""
        regimes: dict[str, list[float]] = {}
        for t in self.trades:
            if t.action in ("BUY", "SELL"):
                regimes.setdefault(t.market_regime, []).append(t.pnl_usd)
        return {
            regime: {
                "count": len(pnls),
                "total_pnl": sum(pnls),
                "avg_pnl": sum(pnls) / len(pnls),
                "win_rate": sum(1 for p in pnls if p > 0) / len(pnls) * 100,
            }
            for regime, pnls in regimes.items()
        }

    def confidence_vs_accuracy(self) -> list[dict]:
        """Map confidence levels to actual win rates."""
        buckets: dict[str, list[bool]] = {}
        for t in self.trades:
            if t.action in ("BUY", "SELL"):
                bucket = f"{int(t.confidence * 10) * 10}-{int(t.confidence * 10) * 10 + 10}%"
                buckets.setdefault(bucket, []).append(t.pnl_usd > 0)
        return [
            {
                "range": k,
                "trades": len(v),
                "win_rate": sum(v) / len(v) * 100 if v else 0,
            }
            for k, v in sorted(buckets.items())
        ]

    # ────────────────────────────────────────────────────────
    #  Full Report
    # ────────────────────────────────────────────────────────

    def get_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        executed = [t for t in self.trades if t.action in ("BUY", "SELL")]
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_pnl": self.total_pnl(),
            "total_return_pct": self.total_return_pct(),
            "total_trades": len(executed),
            "win_rate": self.win_rate(),
            "profit_factor": self.profit_factor(),
            "sharpe_ratio": self.sharpe_ratio(),
            "sortino_ratio": self.sortino_ratio(),
            "calmar_ratio": self.calmar_ratio(),
            "max_drawdown_usd": self.max_drawdown_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "rolling_volatility": self.rolling_volatility(),
            "average_trade_pnl": self.average_trade_pnl(),
            "best_trade": self.best_trade(),
            "worst_trade": self.worst_trade(),
            "peak_equity": self.peak_equity,
            "equity_curve_points": len(self.equity_curve),
            "session_duration_hours": (time.time() - self._session_start) / 3600,
            "regime_breakdown": self.trades_by_regime(),
            "confidence_calibration": self.confidence_vs_accuracy(),
        }

    def format_report(self) -> str:
        """Pretty-print the performance report."""
        r = self.get_report()
        lines = [
            "═" * 55,
            "  PROTOCOL ZERO — PERFORMANCE REPORT",
            "═" * 55,
            f"  Capital:  ${r['initial_capital']:,.2f} → ${r['current_capital']:,.2f}",
            f"  Return:   {r['total_return_pct']:+.2f}%  (PnL ${r['total_pnl']:+.2f})",
            "─" * 55,
            f"  Sharpe Ratio:    {r['sharpe_ratio']:.3f}",
            f"  Sortino Ratio:   {r['sortino_ratio']:.3f}",
            f"  Calmar Ratio:    {r['calmar_ratio']:.3f}",
            f"  Profit Factor:   {r['profit_factor']:.2f}",
            f"  Win Rate:        {r['win_rate']:.1f}%  ({r['total_trades']} trades)",
            f"  Max Drawdown:    {r['max_drawdown_pct']:.2f}% (${r['max_drawdown_usd']:,.2f})",
            f"  Rolling Vol:     {r['rolling_volatility']:.4f}",
            "─" * 55,
            f"  Best Trade:      ${r['best_trade']:+.2f}",
            f"  Worst Trade:     ${r['worst_trade']:+.2f}",
            f"  Avg Trade PnL:   ${r['average_trade_pnl']:+.2f}",
            f"  Peak Equity:     ${r['peak_equity']:,.2f}",
            "═" * 55,
        ]
        return "\n".join(lines)

    # ────────────────────────────────────────────────────────
    #  Persistence
    # ────────────────────────────────────────────────────────

    def _save_history(self) -> None:
        """Persist trade history and equity curve to disk."""
        try:
            data = {
                "initial_capital": self.initial_capital,
                "current_capital": self.current_capital,
                "peak_equity": self.peak_equity,
                "max_drawdown_usd": self.max_drawdown_usd,
                "max_drawdown_pct": self.max_drawdown_pct,
                "session_start": self._session_start,
                "trades": [
                    {
                        "timestamp": t.timestamp,
                        "action": t.action,
                        "asset": t.asset,
                        "amount_usd": t.amount_usd,
                        "pnl_usd": t.pnl_usd,
                        "confidence": t.confidence,
                        "risk_score": t.risk_score,
                        "market_regime": t.market_regime,
                        "entry_price": t.entry_price,
                        "exit_price": t.exit_price,
                    }
                    for t in self.trades
                ],
                "equity_curve": self.equity_curve,
            }
            _PERF_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save performance history: %s", exc)

    def _load_history(self) -> None:
        """Load trade history from disk if available."""
        if not _PERF_FILE.exists():
            return
        try:
            data = json.loads(_PERF_FILE.read_text(encoding="utf-8"))
            self.current_capital = data.get("current_capital", self.initial_capital)
            self.peak_equity = data.get("peak_equity", self.initial_capital)
            self.max_drawdown_usd = data.get("max_drawdown_usd", 0.0)
            self.max_drawdown_pct = data.get("max_drawdown_pct", 0.0)
            self._session_start = data.get("session_start", time.time())
            self.equity_curve = data.get("equity_curve", self.equity_curve)
            for td in data.get("trades", []):
                self.trades.append(TradeRecord(**td))
            logger.info("📂 Loaded %d trades from history", len(self.trades))
        except Exception as exc:
            logger.warning("Failed to load performance history: %s", exc)

    def reset(self) -> None:
        """Reset all performance data."""
        self.current_capital = self.initial_capital
        self.peak_equity = self.initial_capital
        self.max_drawdown_usd = 0.0
        self.max_drawdown_pct = 0.0
        self.trades.clear()
        self.equity_curve = [
            {"timestamp": time.time(), "equity": self.initial_capital, "pnl": 0.0}
        ]
        self._session_start = time.time()
        if _PERF_FILE.exists():
            _PERF_FILE.unlink()
        logger.info("🔄 Performance tracker reset.")


# ════════════════════════════════════════════════════════════
#  CLI Smoke Test
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    tracker = PerformanceTracker(initial_capital=10_000.0)

    # Simulate trades
    test_trades = [
        ("BUY",  "ETH", 500, 35.0, 0.82, 4, "TRENDING"),
        ("SELL", "BTC", 300, -12.5, 0.65, 6, "RANGING"),
        ("BUY",  "ETH", 400, 22.0, 0.78, 3, "TRENDING"),
        ("SELL", "SOL", 200, -45.0, 0.55, 8, "VOLATILE"),
        ("BUY",  "BTC", 600, 88.0, 0.91, 2, "TRENDING"),
        ("SELL", "ETH", 350, 15.0, 0.70, 5, "RANGING"),
    ]

    for action, asset, amount, pnl, conf, risk, regime in test_trades:
        tracker.record_trade(action, asset, amount, pnl, conf, risk, regime)

    print(tracker.format_report())
    print()
    print("Regime Breakdown:", json.dumps(tracker.trades_by_regime(), indent=2))
    print("Confidence Calibration:", json.dumps(tracker.confidence_vs_accuracy(), indent=2))
