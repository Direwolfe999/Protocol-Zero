"""
Protocol Zero — Nova Sonic Voice Unit Tests
=============================================
Tests the voice command parser, text fallback responses,
and VoiceResponse/VoiceCommand data classes.
No AWS credentials required — tests the text-mode path.
"""

from __future__ import annotations

import pytest

from nova_sonic_voice import NovaSonicVoice, VoiceCommand, VoiceResponse


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def voice() -> NovaSonicVoice:
    """Create a voice engine (will use text fallback since no AWS)."""
    return NovaSonicVoice()


@pytest.fixture
def context() -> dict:
    return {
        "session_pnl": 125.50,
        "trade_count": 7,
        "reputation_score": 82,
        "market_regime": "TRENDING",
        "risk_score": 4,
        "open_positions": 2,
        "total_exposure_usd": 1200.0,
        "wallet_eth": 1.5,
        "wallet_weth": 0.3,
        "wallet_usdc": 500.0,
    }


# ════════════════════════════════════════════════════════════
#  Command Parser
# ════════════════════════════════════════════════════════════

class TestCommandParser:
    def test_status_command(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("what is my status")
        assert cmd.intent == "status"
        assert cmd.confidence > 0.0

    def test_kill_switch_command(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("emergency stop")
        assert cmd.intent == "kill_switch"

    def test_trade_confirm(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("execute the trade")
        assert cmd.intent == "trade_confirm"

    def test_risk_query(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("what is my risk exposure")
        assert cmd.intent == "risk_query"

    def test_balance_query(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("how much eth do I have")
        assert cmd.intent == "balance"

    def test_unknown_command(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("tell me a joke about crypto")
        assert cmd.intent == "unknown"
        assert cmd.confidence == 0.0

    def test_wake_word_stripped(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("Protocol Zero, what is my status")
        assert cmd.intent == "status"

    def test_asset_extraction(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("what is my eth balance")
        assert cmd.asset == "ETH"

    def test_btc_asset(self, voice: NovaSonicVoice) -> None:
        cmd = voice._parse_command("how much btc")
        assert cmd.asset == "BTC"


# ════════════════════════════════════════════════════════════
#  Text Fallback Responses
# ════════════════════════════════════════════════════════════

class TestTextFallback:
    def test_status_response(self, voice: NovaSonicVoice, context: dict) -> None:
        resp = voice.process_voice_text("status", context)
        assert isinstance(resp, VoiceResponse)
        assert resp.success is True
        assert resp.intent_handled == "status"
        assert "P&L" in resp.text or "status" in resp.text.lower()

    def test_kill_switch_response(self, voice: NovaSonicVoice) -> None:
        resp = voice.process_voice_text("emergency stop")
        assert resp.intent_handled == "kill_switch"
        assert "halt" in resp.text.lower() or "stop" in resp.text.lower()

    def test_risk_response(self, voice: NovaSonicVoice, context: dict) -> None:
        resp = voice.process_voice_text("risk assessment", context)
        assert resp.intent_handled == "risk_query"
        assert resp.success is True

    def test_unknown_response(self, voice: NovaSonicVoice) -> None:
        resp = voice.process_voice_text("something random xyz")
        assert resp.intent_handled == "unknown"
        assert "Available commands" in resp.text


# ════════════════════════════════════════════════════════════
#  Alerts & Status
# ════════════════════════════════════════════════════════════

class TestAlerts:
    def test_volatility_alert(self, voice: NovaSonicVoice) -> None:
        resp = voice.generate_alert("volatility_spike", {"asset": "ETH", "volatility": 8.5})
        assert resp.success is True
        assert "ETH" in resp.text

    def test_trade_executed_alert(self, voice: NovaSonicVoice) -> None:
        resp = voice.generate_alert("trade_executed", {"action": "BUY", "asset": "ETH", "amount": 500})
        assert "BUY" in resp.text

    def test_unknown_alert_type(self, voice: NovaSonicVoice) -> None:
        resp = voice.generate_alert("some_new_alert", {})
        assert resp.success is True

    def test_status_dict(self, voice: NovaSonicVoice) -> None:
        status = voice.status()
        assert status["enabled"] is True  # Always functional (text mode)
        assert "commands_supported" in status
        assert isinstance(status["commands_supported"], list)


# ════════════════════════════════════════════════════════════
#  Data Classes
# ════════════════════════════════════════════════════════════

class TestDataClasses:
    def test_voice_command_to_dict(self) -> None:
        cmd = VoiceCommand(raw_text="test", intent="status", confidence=0.9)
        d = cmd.to_dict()
        assert d["intent"] == "status"
        assert d["confidence"] == 0.9

    def test_voice_response_to_dict(self) -> None:
        resp = VoiceResponse(text="hello", success=True)
        d = resp.to_dict()
        assert d["text"] == "hello"
        assert d["success"] is True
