"""
Protocol Zero — Performance Tracker Unit Tests
================================================
Tests the PerformanceTracker metrics: Sharpe, drawdown, win rate, etc.
Pure computation — no AWS or blockchain required.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import numpy as np
import pytest

from performance_tracker import PerformanceTracker, TradeRecord


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def tracker() -> PerformanceTracker:
    """Create a fresh tracker that does NOT load from disk."""
    with patch.object(PerformanceTracker, "_load_history"):
        return PerformanceTracker(initial_capital=10_000.0)


@pytest.fixture
def trader_with_history() -> PerformanceTracker:
    """Tracker with a mix of winning and losing trades."""
    with patch.object(PerformanceTracker, "_load_history"):
        t = PerformanceTracker(initial_capital=10_000.0)
    t.record_trade("BUY",  "ETH", 200.0, pnl_usd=30.0,  confidence=0.8, risk_score=3, market_regime="TRENDING")
    t.record_trade("BUY",  "BTC", 300.0, pnl_usd=-15.0, confidence=0.6, risk_score=5, market_regime="RANGING")
    t.record_trade("SELL", "ETH", 150.0, pnl_usd=45.0,  confidence=0.9, risk_score=2, market_regime="TRENDING")
    t.record_trade("BUY",  "SOL", 100.0, pnl_usd=-5.0,  confidence=0.5, risk_score=4, market_regime="UNCERTAIN")
    t.record_trade("SELL", "BTC", 250.0, pnl_usd=20.0,  confidence=0.7, risk_score=3, market_regime="VOLATILE")
    return t


# ════════════════════════════════════════════════════════════
#  Initialization
# ════════════════════════════════════════════════════════════

class TestInit:
    def test_initial_capital(self, tracker: PerformanceTracker) -> None:
        assert tracker.initial_capital == 10_000.0
        assert tracker.current_capital == 10_000.0

    def test_no_trades(self, tracker: PerformanceTracker) -> None:
        assert len(tracker.trades) == 0

    def test_equity_curve_starts_with_initial(self, tracker: PerformanceTracker) -> None:
        assert len(tracker.equity_curve) >= 1
        assert tracker.equity_curve[0]["equity"] == 10_000.0


# ════════════════════════════════════════════════════════════
#  Trade Recording
# ════════════════════════════════════════════════════════════

class TestRecordTrade:
    def test_trade_recorded(self, tracker: PerformanceTracker) -> None:
        tracker.record_trade("BUY", "ETH", 200.0, pnl_usd=15.0)
        assert len(tracker.trades) == 1
        assert tracker.trades[0].action == "BUY"
        assert tracker.trades[0].asset == "ETH"

    def test_capital_updates(self, tracker: PerformanceTracker) -> None:
        tracker.record_trade("BUY", "ETH", 200.0, pnl_usd=50.0)
        assert tracker.current_capital == 10_050.0

    def test_negative_pnl(self, tracker: PerformanceTracker) -> None:
        tracker.record_trade("BUY", "ETH", 200.0, pnl_usd=-30.0)
        assert tracker.current_capital == 9_970.0

    def test_equity_curve_grows(self, tracker: PerformanceTracker) -> None:
        initial_len = len(tracker.equity_curve)
        tracker.record_trade("BUY", "ETH", 200.0, pnl_usd=10.0)
        assert len(tracker.equity_curve) > initial_len


# ════════════════════════════════════════════════════════════
#  Metrics
# ════════════════════════════════════════════════════════════

class TestMetrics:
    def test_report_has_keys(self, trader_with_history: PerformanceTracker) -> None:
        report = trader_with_history.get_report()
        expected_keys = {"total_trades", "win_rate", "total_pnl", "current_capital"}
        assert expected_keys.issubset(report.keys())

    def test_win_rate(self, trader_with_history: PerformanceTracker) -> None:
        report = trader_with_history.get_report()
        # 3 wins (30, 45, 20) out of 5 trades = 60% — win_rate is a percentage
        assert 50 <= report["win_rate"] <= 70

    def test_total_pnl(self, trader_with_history: PerformanceTracker) -> None:
        report = trader_with_history.get_report()
        expected_pnl = 30 - 15 + 45 - 5 + 20  # = 75
        assert abs(report["total_pnl"] - expected_pnl) < 0.01

    def test_total_trades(self, trader_with_history: PerformanceTracker) -> None:
        report = trader_with_history.get_report()
        assert report["total_trades"] == 5

    def test_drawdown_non_negative(self, trader_with_history: PerformanceTracker) -> None:
        assert trader_with_history.max_drawdown_usd >= 0
        assert trader_with_history.max_drawdown_pct >= 0

    def test_empty_tracker_report(self, tracker: PerformanceTracker) -> None:
        report = tracker.get_report()
        assert report["total_trades"] == 0
        assert report["total_pnl"] == 0.0
