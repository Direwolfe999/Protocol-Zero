"""
Protocol Zero — EIP-712 Signer Unit Tests
==========================================
Tests the EIP-712 message builder, signer, and nonce tracker.
No RPC connection required — pure cryptographic tests.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Patch config before importing the module
os.environ.setdefault("RPC_URL", "http://localhost:8545")
os.environ.setdefault("PRIVATE_KEY", "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
os.environ.setdefault("CHAIN_ID", "31337")
os.environ.setdefault("IDENTITY_REGISTRY_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
os.environ.setdefault("REPUTATION_REGISTRY_ADDRESS", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")
os.environ.setdefault("VALIDATION_REGISTRY_ADDRESS", "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0")

from eip712_signer import (
    build_intent_message,
    sign_intent,
    build_and_sign_intent,
    recover_signer,
    get_domain,
    TRADE_INTENT_TYPES,
    PRIMARY_TYPE,
    _NonceTracker,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_order() -> dict:
    return {"token": "ETH", "amount": 250.0, "direction": "BUY"}


@pytest.fixture
def sell_order() -> dict:
    return {"token": "BTC", "amount": 100.0, "direction": "SELL"}


# ════════════════════════════════════════════════════════════
#  Domain & Types
# ════════════════════════════════════════════════════════════

class TestDomain:
    def test_domain_has_required_keys(self) -> None:
        domain = get_domain()
        assert "name" in domain
        assert "version" in domain
        assert "chainId" in domain
        assert "verifyingContract" in domain

    def test_domain_name_is_protocol_zero(self) -> None:
        assert get_domain()["name"] == "ProtocolZero"

    def test_types_has_trade_intent(self) -> None:
        assert "TradeIntent" in TRADE_INTENT_TYPES
        fields = TRADE_INTENT_TYPES["TradeIntent"]
        names = [f["name"] for f in fields]
        assert "action" in names
        assert "nonce" in names
        assert "expiry" in names


# ════════════════════════════════════════════════════════════
#  Message Builder
# ════════════════════════════════════════════════════════════

class TestBuildIntentMessage:
    def test_returns_all_fields(self, sample_order: dict) -> None:
        msg = build_intent_message(sample_order, confidence=0.8)
        assert msg["action"] == "BUY"
        assert msg["asset"] == "ETH"
        assert msg["amountUsd"] == 25000  # 250 * 100 cents
        assert msg["confidence"] == 8000  # 0.8 * 10000 bps
        assert "nonce" in msg
        assert "expiry" in msg
        assert "agent" in msg

    def test_sell_direction(self, sell_order: dict) -> None:
        msg = build_intent_message(sell_order)
        assert msg["action"] == "SELL"

    def test_invalid_direction_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid direction"):
            build_intent_message({"token": "ETH", "amount": 100, "direction": "YOLO"})

    def test_nonce_increments(self, sample_order: dict) -> None:
        msg1 = build_intent_message(sample_order)
        msg2 = build_intent_message(sample_order)
        assert msg2["nonce"] > msg1["nonce"]

    def test_expiry_is_future(self, sample_order: dict) -> None:
        import time
        msg = build_intent_message(sample_order, ttl_seconds=300)
        assert msg["expiry"] > int(time.time())


# ════════════════════════════════════════════════════════════
#  Signing & Verification
# ════════════════════════════════════════════════════════════

class TestSignIntent:
    def test_sign_returns_signature(self, sample_order: dict) -> None:
        msg = build_intent_message(sample_order, confidence=0.82)
        result = sign_intent(msg)
        assert "signature" in result
        assert "intent_hash" in result
        assert "signer" in result
        assert len(result["signature"]) == 65

    def test_round_trip_verification(self, sample_order: dict) -> None:
        result = build_and_sign_intent(sample_order, confidence=0.75)
        recovered = recover_signer(result["message"], result["signature"])
        assert recovered == result["signer"]

    def test_different_messages_different_hashes(self) -> None:
        r1 = build_and_sign_intent({"token": "ETH", "amount": 100, "direction": "BUY"})
        r2 = build_and_sign_intent({"token": "BTC", "amount": 200, "direction": "SELL"})
        assert r1["intent_hash"] != r2["intent_hash"]


# ════════════════════════════════════════════════════════════
#  Nonce Tracker Persistence
# ════════════════════════════════════════════════════════════

class TestNonceTracker:
    def test_nonce_increments(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            tracker = _NonceTracker(_path=path)
            n1 = tracker.next()
            n2 = tracker.next()
            assert n2 == n1 + 1
        finally:
            path.unlink(missing_ok=True)

    def test_nonce_persists_to_disk(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            tracker1 = _NonceTracker(_path=path)
            tracker1.next()
            tracker1.next()
            tracker1.next()
            saved_nonce = tracker1.current

            # Create a new tracker reading the same file
            tracker2 = _NonceTracker(_path=path)
            assert tracker2.current == saved_nonce
        finally:
            path.unlink(missing_ok=True)

    def test_nonce_survives_missing_file(self) -> None:
        path = Path("/tmp/nonexistent_nonce_file.json")
        path.unlink(missing_ok=True)
        tracker = _NonceTracker(_path=path)
        assert tracker.current == 0
        path.unlink(missing_ok=True)
