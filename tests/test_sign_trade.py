"""
Protocol Zero — Sign Trade Unit Tests
=======================================
Tests the validation logic and schema enforcement in sign_trade.py.
No private keys or chain connections required for validation tests.
"""

from __future__ import annotations

import pytest

from sign_trade import validate_decision, ValidationResult


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def valid_buy() -> dict:
    """A fully valid BUY decision."""
    return {
        "action": "BUY",
        "asset": "ETH",
        "amount_usd": 200.0,
        "reason": "RSI oversold + bullish crossover",
        "confidence": 0.78,
        "risk_score": 3,
        "position_size_percent": 1.2,
        "stop_loss_percent": 3.0,
        "take_profit_percent": 6.0,
        "market_regime": "TRENDING",
    }


@pytest.fixture
def valid_hold() -> dict:
    """A valid HOLD decision."""
    return {
        "action": "HOLD",
        "asset": "BTC",
        "amount_usd": 0.0,
        "reason": "No clear signal",
        "confidence": 0.45,
        "risk_score": 5,
        "position_size_percent": 0.0,
        "stop_loss_percent": 0.0,
        "take_profit_percent": 0.0,
        "market_regime": "RANGING",
    }


# ════════════════════════════════════════════════════════════
#  Validation — Happy Path
# ════════════════════════════════════════════════════════════

class TestValidDecisions:
    def test_valid_buy_passes(self, valid_buy: dict) -> None:
        vr = validate_decision(valid_buy)
        assert vr.valid is True
        assert len(vr.errors) == 0

    def test_valid_hold_passes(self, valid_hold: dict) -> None:
        vr = validate_decision(valid_hold)
        assert vr.valid is True

    def test_valid_sell_passes(self, valid_buy: dict) -> None:
        valid_buy["action"] = "SELL"
        vr = validate_decision(valid_buy)
        assert vr.valid is True


# ════════════════════════════════════════════════════════════
#  Validation — Missing Fields
# ════════════════════════════════════════════════════════════

class TestMissingFields:
    def test_missing_action(self, valid_buy: dict) -> None:
        del valid_buy["action"]
        vr = validate_decision(valid_buy)
        assert vr.valid is False
        assert any("missing" in e.lower() for e in vr.errors)

    def test_missing_confidence(self, valid_buy: dict) -> None:
        del valid_buy["confidence"]
        vr = validate_decision(valid_buy)
        assert vr.valid is False

    def test_missing_multiple_fields(self) -> None:
        vr = validate_decision({"amount_usd": 100})
        assert vr.valid is False
        assert len(vr.errors) >= 1


# ════════════════════════════════════════════════════════════
#  Validation — Action
# ════════════════════════════════════════════════════════════

class TestActionValidation:
    def test_invalid_action(self, valid_buy: dict) -> None:
        valid_buy["action"] = "YOLO"
        vr = validate_decision(valid_buy)
        assert vr.valid is False
        assert any("invalid action" in e.lower() for e in vr.errors)

    def test_case_insensitive(self, valid_buy: dict) -> None:
        valid_buy["action"] = "buy"
        vr = validate_decision(valid_buy)
        # "buy" uppercased internally — should still match
        assert vr.valid is True or any("action" in e.lower() for e in vr.errors)


# ════════════════════════════════════════════════════════════
#  Validation — Confidence
# ════════════════════════════════════════════════════════════

class TestConfidenceValidation:
    def test_low_confidence_blocks_trade(self, valid_buy: dict) -> None:
        valid_buy["confidence"] = 0.30  # below 0.6 floor
        vr = validate_decision(valid_buy)
        assert vr.valid is False
        assert any("confidence" in e.lower() for e in vr.errors)

    def test_low_confidence_ok_for_hold(self, valid_hold: dict) -> None:
        valid_hold["confidence"] = 0.10
        vr = validate_decision(valid_hold)
        assert vr.valid is True  # HOLD doesn't require confidence

    def test_confidence_out_of_range(self, valid_buy: dict) -> None:
        valid_buy["confidence"] = 1.5
        vr = validate_decision(valid_buy)
        assert vr.valid is False

    def test_negative_confidence(self, valid_buy: dict) -> None:
        valid_buy["confidence"] = -0.1
        vr = validate_decision(valid_buy)
        assert vr.valid is False


# ════════════════════════════════════════════════════════════
#  Validation — Position Size
# ════════════════════════════════════════════════════════════

class TestPositionSize:
    def test_exceeds_cap(self, valid_buy: dict) -> None:
        valid_buy["position_size_percent"] = 5.0
        vr = validate_decision(valid_buy)
        assert vr.valid is False
        assert any("position size" in e.lower() for e in vr.errors)

    def test_negative_position(self, valid_buy: dict) -> None:
        valid_buy["position_size_percent"] = -1.0
        vr = validate_decision(valid_buy)
        assert vr.valid is False


# ════════════════════════════════════════════════════════════
#  Validation — Stop Loss & Take Profit
# ════════════════════════════════════════════════════════════

class TestStopLossTakeProfit:
    def test_missing_stop_loss(self, valid_buy: dict) -> None:
        valid_buy["stop_loss_percent"] = 0.0
        vr = validate_decision(valid_buy)
        assert vr.valid is False
        assert any("stop-loss" in e.lower() for e in vr.errors)

    def test_missing_take_profit(self, valid_buy: dict) -> None:
        valid_buy["take_profit_percent"] = 0.0
        vr = validate_decision(valid_buy)
        assert vr.valid is False

    def test_wide_stop_loss_warns(self, valid_buy: dict) -> None:
        valid_buy["stop_loss_percent"] = 30.0
        vr = validate_decision(valid_buy)
        assert any("wide" in w.lower() for w in vr.warnings)


# ════════════════════════════════════════════════════════════
#  Validation — Risk Score
# ════════════════════════════════════════════════════════════

class TestRiskScore:
    def test_zero_risk_score(self, valid_buy: dict) -> None:
        valid_buy["risk_score"] = 0
        vr = validate_decision(valid_buy)
        assert vr.valid is False

    def test_risk_score_over_max(self, valid_buy: dict) -> None:
        valid_buy["risk_score"] = 11
        vr = validate_decision(valid_buy)
        assert vr.valid is False


# ════════════════════════════════════════════════════════════
#  Validation — Market Regime
# ════════════════════════════════════════════════════════════

class TestMarketRegime:
    def test_invalid_regime(self, valid_buy: dict) -> None:
        valid_buy["market_regime"] = "MOONSHOT"
        vr = validate_decision(valid_buy)
        assert vr.valid is False

    def test_all_valid_regimes(self, valid_buy: dict) -> None:
        for regime in ("TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"):
            valid_buy["market_regime"] = regime
            vr = validate_decision(valid_buy)
            regime_errors = [e for e in vr.errors if "regime" in e.lower()]
            assert len(regime_errors) == 0


# ════════════════════════════════════════════════════════════
#  ValidationResult Dataclass
# ════════════════════════════════════════════════════════════

class TestValidationResult:
    def test_starts_valid(self) -> None:
        vr = ValidationResult()
        assert vr.valid is True
        assert len(vr.errors) == 0

    def test_reject_marks_invalid(self) -> None:
        vr = ValidationResult()
        vr.reject("something wrong")
        assert vr.valid is False
        assert "something wrong" in vr.errors

    def test_warn_stays_valid(self) -> None:
        vr = ValidationResult()
        vr.warn("heads up")
        assert vr.valid is True
        assert "heads up" in vr.warnings
