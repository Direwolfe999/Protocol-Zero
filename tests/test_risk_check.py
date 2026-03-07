"""
Protocol Zero — Risk Check Unit Tests
=======================================
Tests all 6 risk checks and the composite run_all_checks() gate.
These are pure-logic tests with no network or chain dependencies.
"""

from __future__ import annotations

import time

import pytest

from risk_check import (
    RiskState,
    check_max_position_size,
    check_daily_loss_limit,
    check_trade_frequency,
    check_concentration,
    check_confidence_floor,
    check_intent_expiry,
    run_all_checks,
    format_risk_report,
)


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def state() -> RiskState:
    """Fresh risk state with conservative defaults."""
    return RiskState(
        max_position_usd=500.0,
        max_daily_loss_usd=1000.0,
        total_capital_usd=10_000.0,
        min_confidence=0.40,
        max_trades_per_hour=10,
        max_concentration_pct=0.30,
    )


@pytest.fixture
def buy_decision() -> dict:
    """A valid BUY decision that should pass all checks."""
    return {
        "action": "BUY",
        "asset": "ETH",
        "amount_usd": 200.0,
        "confidence": 0.75,
        "risk_score": 3,
    }


@pytest.fixture
def hold_decision() -> dict:
    return {
        "action": "HOLD",
        "asset": "ETH",
        "amount_usd": 0.0,
        "confidence": 0.10,
    }


# ════════════════════════════════════════════════════════════
#  check_max_position_size
# ════════════════════════════════════════════════════════════

class TestMaxPositionSize:
    def test_within_limit(self, state: RiskState, buy_decision: dict) -> None:
        passed, msg = check_max_position_size(state, buy_decision)
        assert passed is True
        assert "OK" in msg

    def test_exceeds_limit(self, state: RiskState) -> None:
        decision = {"action": "BUY", "asset": "BTC", "amount_usd": 9999.0}
        passed, msg = check_max_position_size(state, decision)
        assert passed is False
        assert "exceeds" in msg.lower()

    def test_zero_amount_non_hold(self, state: RiskState) -> None:
        decision = {"action": "BUY", "asset": "ETH", "amount_usd": 0.0}
        passed, msg = check_max_position_size(state, decision)
        assert passed is False

    def test_exact_limit(self, state: RiskState) -> None:
        decision = {"action": "BUY", "asset": "ETH", "amount_usd": 500.0}
        passed, msg = check_max_position_size(state, decision)
        assert passed is True


# ════════════════════════════════════════════════════════════
#  check_daily_loss_limit
# ════════════════════════════════════════════════════════════

class TestDailyLossLimit:
    def test_no_losses(self, state: RiskState, buy_decision: dict) -> None:
        passed, _ = check_daily_loss_limit(state, buy_decision)
        assert passed is True

    def test_at_limit(self, state: RiskState, buy_decision: dict) -> None:
        state.daily_pnl_usd = -1000.0
        passed, msg = check_daily_loss_limit(state, buy_decision)
        assert passed is False
        assert "loss limit" in msg.lower()

    def test_beyond_limit(self, state: RiskState, buy_decision: dict) -> None:
        state.daily_pnl_usd = -1500.0
        passed, _ = check_daily_loss_limit(state, buy_decision)
        assert passed is False

    def test_positive_pnl(self, state: RiskState, buy_decision: dict) -> None:
        state.daily_pnl_usd = 500.0
        passed, _ = check_daily_loss_limit(state, buy_decision)
        assert passed is True


# ════════════════════════════════════════════════════════════
#  check_trade_frequency
# ════════════════════════════════════════════════════════════

class TestTradeFrequency:
    def test_no_trades(self, state: RiskState, buy_decision: dict) -> None:
        passed, _ = check_trade_frequency(state, buy_decision)
        assert passed is True

    def test_rate_limit_hit(self, state: RiskState, buy_decision: dict) -> None:
        now = time.time()
        state.trade_timestamps = [now - i for i in range(10)]  # 10 trades in last hour
        passed, msg = check_trade_frequency(state, buy_decision)
        assert passed is False
        assert "rate limit" in msg.lower()

    def test_old_trades_ignored(self, state: RiskState, buy_decision: dict) -> None:
        state.trade_timestamps = [time.time() - 7200] * 20  # all 2 hours ago
        passed, _ = check_trade_frequency(state, buy_decision)
        assert passed is True


# ════════════════════════════════════════════════════════════
#  check_concentration
# ════════════════════════════════════════════════════════════

class TestConcentration:
    def test_no_existing_position(self, state: RiskState, buy_decision: dict) -> None:
        passed, _ = check_concentration(state, buy_decision)
        assert passed is True

    def test_exceeds_concentration(self, state: RiskState) -> None:
        state.positions["ETH"] = 2500.0  # 25% already
        decision = {"action": "BUY", "asset": "ETH", "amount_usd": 1000.0}
        passed, msg = check_concentration(state, decision)
        assert passed is False
        assert "concentration" in msg.lower()

    def test_different_assets_ok(self, state: RiskState) -> None:
        state.positions["BTC"] = 2000.0
        decision = {"action": "BUY", "asset": "ETH", "amount_usd": 200.0}
        passed, _ = check_concentration(state, decision)
        assert passed is True


# ════════════════════════════════════════════════════════════
#  check_confidence_floor
# ════════════════════════════════════════════════════════════

class TestConfidenceFloor:
    def test_above_threshold(self, state: RiskState, buy_decision: dict) -> None:
        passed, _ = check_confidence_floor(state, buy_decision)
        assert passed is True

    def test_below_threshold(self, state: RiskState) -> None:
        decision = {"action": "BUY", "asset": "ETH", "confidence": 0.10}
        passed, msg = check_confidence_floor(state, decision)
        assert passed is False

    def test_at_threshold(self, state: RiskState) -> None:
        decision = {"action": "BUY", "asset": "ETH", "confidence": 0.40}
        passed, _ = check_confidence_floor(state, decision)
        assert passed is True


# ════════════════════════════════════════════════════════════
#  check_intent_expiry
# ════════════════════════════════════════════════════════════

class TestIntentExpiry:
    def test_no_expiry(self, state: RiskState, buy_decision: dict) -> None:
        passed, msg = check_intent_expiry(state, buy_decision)
        assert passed is True
        assert "skipping" in msg.lower()

    def test_valid_expiry(self, state: RiskState, buy_decision: dict) -> None:
        buy_decision["expiry"] = int(time.time()) + 300
        passed, _ = check_intent_expiry(state, buy_decision)
        assert passed is True

    def test_expired(self, state: RiskState, buy_decision: dict) -> None:
        buy_decision["expiry"] = int(time.time()) - 10
        passed, msg = check_intent_expiry(state, buy_decision)
        assert passed is False
        assert "expired" in msg.lower()


# ════════════════════════════════════════════════════════════
#  run_all_checks (composite)
# ════════════════════════════════════════════════════════════

class TestRunAllChecks:
    def test_valid_trade_passes(self, state: RiskState, buy_decision: dict) -> None:
        passed, messages = run_all_checks(state, buy_decision)
        assert passed is True
        assert all("✅" in m for m in messages)

    def test_hold_always_passes(self, state: RiskState, hold_decision: dict) -> None:
        passed, messages = run_all_checks(state, hold_decision)
        assert passed is True
        assert len(messages) == 1

    def test_multiple_failures(self, state: RiskState) -> None:
        state.daily_pnl_usd = -2000.0
        decision = {
            "action": "BUY",
            "asset": "ETH",
            "amount_usd": 9999.0,
            "confidence": 0.05,
        }
        passed, messages = run_all_checks(state, decision)
        assert passed is False
        failed = [m for m in messages if "❌" in m]
        assert len(failed) >= 2  # at least position size + daily loss + confidence

    def test_record_trade_updates_state(self, state: RiskState) -> None:
        state.record_trade("ETH", 200.0, pnl_usd=-50.0)
        assert state.positions["ETH"] == 200.0
        assert state.daily_pnl_usd == -50.0
        assert state.trade_count == 1

    def test_reset_daily_clears(self, state: RiskState) -> None:
        state.record_trade("ETH", 200.0, pnl_usd=-50.0)
        state.reset_daily()
        assert state.daily_pnl_usd == 0.0
        assert state.trade_count == 0


# ════════════════════════════════════════════════════════════
#  format_risk_report
# ════════════════════════════════════════════════════════════

class TestFormatRiskReport:
    def test_report_contains_header(self, state: RiskState, buy_decision: dict) -> None:
        report = format_risk_report(state, buy_decision)
        assert "RISK GATE" in report
        assert "PASSED" in report

    def test_blocked_report(self, state: RiskState) -> None:
        decision = {"action": "BUY", "asset": "ETH", "amount_usd": 9999.0, "confidence": 0.8}
        report = format_risk_report(state, decision)
        assert "BLOCKED" in report
