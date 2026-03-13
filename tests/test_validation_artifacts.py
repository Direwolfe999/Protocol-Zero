"""
Protocol Zero — Validation Artifacts Unit Tests
=================================================
Tests the validation artifact builder, hashing, and local storage.
No AWS or blockchain required — tests the artifact data structures.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("RPC_URL", "http://localhost:8545")
os.environ.setdefault("PRIVATE_KEY", "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
os.environ.setdefault("CHAIN_ID", "31337")
os.environ.setdefault("IDENTITY_REGISTRY_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
os.environ.setdefault("REPUTATION_REGISTRY_ADDRESS", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")
os.environ.setdefault("VALIDATION_REGISTRY_ADDRESS", "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0")

from validation_artifacts import ValidationArtifact


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_decision() -> dict:
    return {
        "action": "BUY",
        "asset": "ETH",
        "amount_usd": 200.0,
        "reason": "RSI oversold + bullish crossover",
        "confidence": 0.82,
        "risk_score": 3,
        "position_size_percent": 1.2,
        "stop_loss_percent": 3.0,
        "take_profit_percent": 6.0,
        "market_regime": "TRENDING",
    }


@pytest.fixture
def sample_risk_checks() -> list[dict]:
    return [
        {"check": "max_position_size", "passed": True, "detail": "$200 <= $500 limit"},
        {"check": "daily_loss_limit", "passed": True, "detail": "-$50 <= -$1000 limit"},
        {"check": "trade_frequency", "passed": True, "detail": "3 trades <= 10/hr limit"},
        {"check": "concentration", "passed": True, "detail": "15% <= 30% limit"},
        {"check": "confidence_floor", "passed": True, "detail": "82% >= 40% minimum"},
        {"check": "intent_expiry", "passed": True, "detail": "Fresh intent (< 5 min)"},
    ]


# ════════════════════════════════════════════════════════════
#  ValidationArtifact Data Class
# ════════════════════════════════════════════════════════════

class TestValidationArtifact:
    def test_create_artifact(self, sample_decision: dict, sample_risk_checks: list) -> None:
        artifact = ValidationArtifact(
            artifact_id="test-001",
            timestamp="2026-01-01T00:00:00Z",
            agent_address="0x1234567890abcdef1234567890abcdef12345678",
            chain_id=31337,
            market_snapshot={"price": 3400.0, "rsi": 28.5},
            decision=sample_decision,
            reasoning_trace="RSI at 28.5 — oversold condition detected",
            risk_checks=sample_risk_checks,
            risk_passed=True,
        )
        assert artifact.artifact_id == "test-001"
        assert artifact.risk_passed is True
        assert artifact.decision["action"] == "BUY"

    def test_artifact_default_fields(self) -> None:
        artifact = ValidationArtifact(
            artifact_id="test-002",
            timestamp="2026-01-01T00:00:00Z",
            agent_address="0x0000",
            chain_id=31337,
            market_snapshot={},
            decision={"action": "HOLD"},
            reasoning_trace="",
            risk_checks=[],
            risk_passed=False,
        )
        assert artifact.signature == ""
        assert artifact.intent_hash == ""
        assert artifact.performance_metrics == {}
        assert artifact.artifact_hash == ""

    def test_artifact_with_signature(self, sample_decision: dict) -> None:
        artifact = ValidationArtifact(
            artifact_id="test-003",
            timestamp="2026-01-01T00:00:00Z",
            agent_address="0xABCD",
            chain_id=11155111,
            market_snapshot={"price": 42000},
            decision=sample_decision,
            reasoning_trace="Strong buy signal",
            risk_checks=[],
            risk_passed=True,
            signature="0xdeadbeef",
            intent_hash="0xcafebabe",
        )
        assert artifact.signature == "0xdeadbeef"
        assert artifact.chain_id == 11155111


# ════════════════════════════════════════════════════════════
#  Artifact Serialization
# ════════════════════════════════════════════════════════════

class TestArtifactSerialization:
    def test_to_dict(self, sample_decision: dict, sample_risk_checks: list) -> None:
        from dataclasses import asdict
        artifact = ValidationArtifact(
            artifact_id="ser-001",
            timestamp="2026-01-01T00:00:00Z",
            agent_address="0x1234",
            chain_id=31337,
            market_snapshot={"price": 3400},
            decision=sample_decision,
            reasoning_trace="test",
            risk_checks=sample_risk_checks,
            risk_passed=True,
        )
        d = asdict(artifact)
        assert isinstance(d, dict)
        assert d["artifact_id"] == "ser-001"
        assert d["risk_passed"] is True

    def test_json_serializable(self, sample_decision: dict) -> None:
        from dataclasses import asdict
        artifact = ValidationArtifact(
            artifact_id="json-001",
            timestamp="2026-01-01T00:00:00Z",
            agent_address="0x1234",
            chain_id=31337,
            market_snapshot={},
            decision=sample_decision,
            reasoning_trace="test",
            risk_checks=[],
            risk_passed=True,
        )
        # Should not raise
        json_str = json.dumps(asdict(artifact), default=str)
        assert isinstance(json_str, str)
        assert "json-001" in json_str
