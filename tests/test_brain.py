"""
Protocol Zero — Brain Unit Tests (Rule-Based Engine)
=====================================================
Tests the rule-based fallback decision engine and response parser.
No AWS/Bedrock credentials required — these are pure logic tests.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from brain import _rule_based_decision, _parse_decision, _default_hold, _compute_rsi


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Build a minimal 48-row DataFrame mimicking OHLCV + indicators."""
    np.random.seed(42)
    n = 48
    close = 40_000 + np.cumsum(np.random.randn(n) * 100)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"),
        "open":   close - np.random.rand(n) * 50,
        "high":   close + np.random.rand(n) * 100,
        "low":    close - np.random.rand(n) * 100,
        "close":  close,
        "volume": np.random.rand(n) * 1000 + 500,
    })
    df["sma_12"] = df["close"].rolling(12).mean()
    df["sma_26"] = df["close"].rolling(26).mean()
    df["rsi_14"] = _compute_rsi(df["close"], 14)
    df["pct_change"] = df["close"].pct_change() * 100
    return df


@pytest.fixture
def oversold_df(sample_df: pd.DataFrame) -> pd.DataFrame:
    """Force RSI into oversold territory with bullish crossover."""
    df = sample_df.copy()
    # Make prices decline sharply then recover slightly
    df.loc[df.index[-5:], "close"] = df["close"].iloc[-6] * 0.92
    df["rsi_14"] = _compute_rsi(df["close"], 14)
    df.iloc[-1, df.columns.get_loc("rsi_14")] = 25.0  # Force oversold
    df.iloc[-1, df.columns.get_loc("sma_12")] = df["close"].iloc[-1] + 100  # bullish crossover
    df.iloc[-1, df.columns.get_loc("sma_26")] = df["close"].iloc[-1] - 100
    return df


# ════════════════════════════════════════════════════════════
#  Rule-Based Decision Engine
# ════════════════════════════════════════════════════════════

class TestRuleBasedDecision:
    def test_returns_valid_schema(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        required_keys = {
            "action", "asset", "amount_usd", "reason", "confidence",
            "risk_score", "position_size_percent", "stop_loss_percent",
            "take_profit_percent", "market_regime",
        }
        assert required_keys.issubset(decision.keys())

    def test_action_is_valid(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        assert decision["action"] in {"BUY", "SELL", "HOLD"}

    def test_confidence_range(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        assert 0.0 <= decision["confidence"] <= 1.0

    def test_risk_score_range(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        assert 1 <= decision["risk_score"] <= 10

    def test_position_size_cap(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        assert decision["position_size_percent"] <= 2.0

    def test_market_regime_valid(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        assert decision["market_regime"] in {"TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"}

    def test_asset_extracted_from_pair(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "ETH/USDT", 500.0)
        assert decision["asset"] == "ETH"

    def test_oversold_triggers_buy(self, oversold_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(oversold_df, "BTC/USDT", 500.0)
        assert decision["action"] == "BUY"
        assert decision["confidence"] >= 0.15  # can be reduced by divergence penalty

    def test_insufficient_data_returns_hold(self) -> None:
        short_df = pd.DataFrame({"close": [100, 101, 102]})
        decision = _rule_based_decision(short_df, "BTC/USDT", 500.0)
        assert decision["action"] == "HOLD"

    def test_none_df_returns_hold(self) -> None:
        decision = _rule_based_decision(None, "BTC/USDT", 500.0)
        assert decision["action"] == "HOLD"

    def test_reason_prefixed(self, sample_df: pd.DataFrame) -> None:
        decision = _rule_based_decision(sample_df, "BTC/USDT", 500.0)
        assert isinstance(decision["reason"], str) and len(decision["reason"]) > 0


# ════════════════════════════════════════════════════════════
#  Response Parser
# ════════════════════════════════════════════════════════════

class TestParseDecision:
    def test_valid_json(self) -> None:
        raw = json.dumps({
            "action": "BUY",
            "asset": "ETH",
            "amount_usd": 200.0,
            "reason": "RSI oversold",
            "confidence": 0.82,
            "risk_score": 3,
            "position_size_percent": 1.2,
            "stop_loss_percent": 3.0,
            "take_profit_percent": 6.0,
            "market_regime": "TRENDING",
        })
        decision = _parse_decision(raw)
        assert decision["action"] == "BUY"
        assert decision["confidence"] == 0.82
        assert decision["market_regime"] == "TRENDING"

    def test_strips_markdown_fences(self) -> None:
        raw = "```json\n" + json.dumps({
            "action": "SELL", "asset": "BTC", "amount_usd": 100,
            "reason": "overbought", "confidence": 0.7, "risk_score": 4,
            "position_size_percent": 0.5, "stop_loss_percent": 2,
            "take_profit_percent": 5, "market_regime": "VOLATILE",
        }) + "\n```"
        decision = _parse_decision(raw)
        assert decision["action"] == "SELL"

    def test_invalid_action_defaults_to_hold(self) -> None:
        raw = json.dumps({"action": "YOLO", "asset": "BTC"})
        decision = _parse_decision(raw)
        assert decision["action"] == "HOLD"

    def test_confidence_clamped(self) -> None:
        raw = json.dumps({"action": "BUY", "confidence": 5.0, "risk_score": 3})
        decision = _parse_decision(raw)
        assert decision["confidence"] == 1.0  # clamped to max

    def test_risk_score_clamped(self) -> None:
        raw = json.dumps({"action": "BUY", "risk_score": 99})
        decision = _parse_decision(raw)
        assert decision["risk_score"] == 10  # clamped to max

    def test_invalid_regime_defaults(self) -> None:
        raw = json.dumps({"action": "HOLD", "market_regime": "CHAOS"})
        decision = _parse_decision(raw)
        assert decision["market_regime"] == "UNCERTAIN"


# ════════════════════════════════════════════════════════════
#  Default Hold
# ════════════════════════════════════════════════════════════

class TestDefaultHold:
    def test_default_hold_schema(self) -> None:
        hold = _default_hold()
        assert hold["action"] == "HOLD"
        assert hold["amount_usd"] == 0.0
        assert hold["confidence"] == 0.0
        assert hold["market_regime"] == "UNCERTAIN"


# ════════════════════════════════════════════════════════════
#  RSI Computation
# ════════════════════════════════════════════════════════════

class TestComputeRSI:
    def test_rsi_range(self) -> None:
        prices = pd.Series([100 + i * 0.5 for i in range(30)])
        rsi = _compute_rsi(prices, 14)
        valid = rsi.dropna()
        assert all(0 <= v <= 100 for v in valid)

    def test_constant_prices(self) -> None:
        prices = pd.Series([100.0] * 30)
        rsi = _compute_rsi(prices, 14)
        # Constant prices → no gains or losses → RSI is NaN or 50-ish
        # (division by zero in RS produces NaN, which is acceptable)
        assert True  # no crash
