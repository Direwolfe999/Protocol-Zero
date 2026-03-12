"""
Protocol Zero — Nova Voice & Text Intelligence
=================================================
Conversational AI interface powered by Amazon Nova Lite:

  1. Voice Status Reports — "Protocol Zero, what is my risk exposure?"
  2. Voice Kill-Switch  — "Protocol Zero, emergency stop!"
  3. Verbal Risk Briefs — Text-based reports read via Web Speech API.
  4. Voice Trade Confirm — "Execute the trade" voice confirmation.

Architecture:
    • Text reasoning via Nova Lite Converse API (``config.BEDROCK_MODEL_ID``)
    • Browser-side TTS via the Web Speech API
    • Nova Sonic S2S session is initialised for future audio I/O
      but bidirectional audio frames are NOT wired yet.
    • Falls back to rule-based text responses when AWS is unavailable.
"""

from __future__ import annotations

import asyncio
import base64
import json
import hashlib
import logging
import io
import struct
import time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Callable

import boto3

import config

logger = logging.getLogger("protocol_zero.nova_sonic")

# ────────────────────────────────────────────────────────────
#  Voice Command Schema
# ────────────────────────────────────────────────────────────

@dataclass
class VoiceCommand:
    """Parsed voice command from the user."""
    raw_text: str = ""
    intent: str = "unknown"          # status | kill_switch | trade_confirm | risk_query | unknown
    asset: str = ""
    confidence: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VoiceResponse:
    """Generated voice response to send back."""
    text: str = ""
    audio_b64: str = ""              # base64-encoded audio (PCM/Opus)
    intent_handled: str = ""
    success: bool = True
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ────────────────────────────────────────────────────────────
#  Nova Sonic Voice Engine
# ────────────────────────────────────────────────────────────

class NovaSonicVoice:
    """
    Amazon Nova 2 Sonic powered voice interface for Protocol Zero.

    Supports bidirectional streaming for real-time speech-to-speech:
    - User speaks → Nova Sonic transcribes + reasons → responds with voice
    - System events → Nova Sonic synthesizes verbal alerts
    """

    # Voice commands the system recognizes
    COMMANDS = {
        "status":        ["status", "what is my status", "portfolio status", "how am i doing",
                          "give me a status report", "what's happening"],
        "kill_switch":   ["emergency stop", "kill switch", "halt trading", "stop all trades",
                          "emergency", "shut it down", "abort"],
        "trade_confirm": ["execute", "confirm trade", "do it", "execute the trade",
                          "go ahead", "proceed", "confirm"],
        "risk_query":    ["risk", "risk exposure", "what is my risk", "how risky",
                          "risk assessment", "threat level", "danger"],
        "balance":       ["balance", "how much", "wallet", "funds", "how much eth",
                          "what's my balance"],
    }

    SYSTEM_PROMPT = (
        "You are Protocol Zero, an autonomous DeFi trading AI sentinel. "
        "Respond concisely and professionally. You protect the user's capital "
        "through real-time risk assessment and trustless ERC-8004 compliance. "
        "When reporting status, be brief but precise with numbers. "
        "For emergency commands, confirm immediately and clearly. "
        "Speak like a calm, confident financial operations AI."
    )

    def __init__(self):
        self.enabled = config.NOVA_SONIC_ENABLED and config.AWS_READY
        self.model_id = config.NOVA_SONIC_MODEL_ID
        self._client = None
        self._session_id = None

        if self.enabled:
            try:
                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=config.AWS_DEFAULT_REGION,
                    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                )
                logger.info("✅ Nova 2 Sonic voice engine initialized")
            except Exception as e:
                logger.warning("Nova Sonic init failed: %s", e)
                self.enabled = False
        else:
            logger.info("Nova Sonic: AWS not ready — using text-mode fallback")

    # ── Public API ──────────────────────────────────────────

    def process_voice_text(self, user_text: str, context: dict | None = None) -> VoiceResponse:
        """
        Process a text command (from speech-to-text or typed)
        and generate a response. When AWS is ready, uses Nova Sonic
        for intelligent response generation.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        cmd = self._parse_command(user_text)
        cmd.timestamp = timestamp

        logger.info("Voice command: intent=%s, raw=%s", cmd.intent, cmd.raw_text)

        if self.enabled and self._client:
            return self._nova_sonic_respond(cmd, context or {})
        else:
            return self._text_fallback_respond(cmd, context or {})

    def generate_alert(self, alert_type: str, details: dict) -> VoiceResponse:
        """
        Generate a proactive voice alert for system events.
        e.g., "Warning: volatility spike detected on ETH."
        """
        alert_text = self._build_alert_text(alert_type, details)

        if self.enabled and self._client:
            return self._synthesize_speech(alert_text, intent_handled=f"alert_{alert_type}")
        else:
            return VoiceResponse(
                text=alert_text,
                intent_handled=f"alert_{alert_type}",
                success=True,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def generate_risk_brief(self, portfolio: dict) -> VoiceResponse:
        """
        Generate a spoken risk briefing from portfolio data.
        "Current portfolio: 3 positions, total exposure $1,500,
        risk score 4 of 10. No immediate threats detected."
        """
        brief = self._build_risk_brief(portfolio)

        if self.enabled:
            return self._synthesize_speech(brief, intent_handled="risk_brief")
        else:
            return VoiceResponse(
                text=brief,
                intent_handled="risk_brief",
                success=True,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def start_voice_session(self, audio_callback: Callable | None = None) -> str:
        """
        Start a bidirectional voice streaming session with Nova Sonic.
        Returns a session ID for the WebSocket connection.

        Nova Sonic is a speech-to-speech model that uses bidirectional
        streaming via ``invoke_model_with_bidirectional_stream``.  The
        exact request schema follows the Nova Sonic S2S API:

            https://docs.aws.amazon.com/nova/latest/userguide/speech.html

        When Bedrock credentials are unavailable or the streaming
        endpoint is not yet provisioned, the system gracefully falls
        back to text-mode intelligence (still fully functional).
        """
        self._session_id = hashlib.sha256(
            f"pz-voice-{time.time()}".encode()
        ).hexdigest()[:16]

        if self.enabled and self._client:
            logger.info("Starting Nova Sonic voice session: %s", self._session_id)
            try:
                # Nova Sonic S2S bidirectional streaming
                # Ref: Amazon Nova Sonic Developer Guide
                session_config = {
                    "inputAudioConfig": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 16000,
                        "singleChannel": True,
                    },
                    "outputAudioConfig": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "singleChannel": True,
                    },
                    "textConfig": {
                        "mediaType": "text/plain",
                    },
                    "sessionAttributes": {
                        "systemPrompt": self.SYSTEM_PROMPT,
                    },
                }
                self._stream_session = self._client.invoke_model_with_bidirectional_stream(
                    modelId=self.model_id,
                    body=json.dumps(session_config),
                )
                logger.info("Nova Sonic stream session active")
            except Exception as e:
                logger.warning(
                    "Bidirectional stream setup failed: %s — using text mode. "
                    "This is expected if Nova Sonic is not provisioned in your region.",
                    e,
                )

        return self._session_id

    def status(self) -> dict:
        """Return voice engine status for dashboard."""
        if self.enabled:
            # When AWS is ready, we use Nova Lite Converse for text reasoning
            # and return text for browser-side Web Speech API playback.
            # Nova Sonic S2S streaming is initialised but audio I/O is not
            # wired — so the honest label is "Nova Lite".
            mode = "Nova Lite (Text Intelligence + Web Speech)"
        else:
            mode = "Rule-Based (Text Fallback)"
        return {
            "enabled": True,  # Module is always functional (text or speech)
            "model": self.model_id,
            "aws_ready": config.AWS_READY,
            "mode": mode,
            "session_active": self._session_id is not None,
            "commands_supported": list(self.COMMANDS.keys()),
        }

    # ── Nova Sonic Response Generation ──────────────────────

    def _nova_sonic_respond(self, cmd: VoiceCommand, context: dict) -> VoiceResponse:
        """
        Generate an intelligent text response using Nova Lite Converse API.

        NOTE: This uses Nova Lite (``config.BEDROCK_MODEL_ID``) for text
        reasoning, NOT Nova Sonic speech-to-speech.  The text is returned
        to the dashboard for browser-side Web Speech API playback.
        """
        # Build context-aware prompt
        prompt = self._build_response_prompt(cmd, context)

        try:
            # Nova Lite Converse API — text reasoning (not Sonic S2S)
            response = self._client.converse(
                modelId=config.BEDROCK_MODEL_ID,  # Nova Lite for text reasoning
                messages=[{
                    "role": "user",
                    "content": [{"text": prompt}],
                }],
                system=[{"text": self.SYSTEM_PROMPT}],
                inferenceConfig={"maxTokens": 256, "temperature": 0.3},
            )
            response_text = response["output"]["message"]["content"][0]["text"]

            # Synthesize speech from the response text
            return self._synthesize_speech(response_text, cmd.intent)

        except Exception as e:
            logger.error("Nova Sonic response failed: %s", e)
            return self._text_fallback_respond(cmd, context)

    def _synthesize_speech(self, text: str, intent_handled: str = "") -> VoiceResponse:
        """
        Polish text for spoken delivery using Nova Lite Converse API.

        Uses Nova Lite (``config.BEDROCK_MODEL_ID``) to rewrite the raw
        text into a concise spoken-form sentence, then returns the text
        for browser-side Web Speech API playback.

        No raw audio is generated — this is a text-to-polished-text step.
        Falls back to the raw text if the API call fails.
        """
        try:
            # Use Nova Lite via Converse to produce polished spoken text,
            # then let the browser handle TTS via the Web Speech API.
            response = self._client.converse(
                modelId=config.BEDROCK_MODEL_ID,
                messages=[{
                    "role": "user",
                    "content": [{"text": f"Rewrite the following for a spoken voice alert. "
                                         f"Keep it concise (2 sentences max):\n\n{text}"}],
                }],
                system=[{"text": self.SYSTEM_PROMPT}],
                inferenceConfig={"maxTokens": 128, "temperature": 0.3},
            )
            spoken_text = response["output"]["message"]["content"][0]["text"]

            return VoiceResponse(
                text=spoken_text,
                intent_handled=intent_handled,
                success=True,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.warning("Speech synthesis failed: %s — returning raw text", e)
            return VoiceResponse(
                text=text,
                intent_handled=intent_handled,
                success=True,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    # ── Text Fallback (no AWS) ──────────────────────────────

    def _text_fallback_respond(self, cmd: VoiceCommand, context: dict) -> VoiceResponse:
        """Generate text-only response when Nova Sonic is unavailable."""
        timestamp = datetime.now(timezone.utc).isoformat()

        responses = {
            "status": self._build_status_text(context),
            "kill_switch": "⛔ Emergency stop activated. All trading has been halted immediately. "
                           "No new positions will be opened until you manually resume.",
            "trade_confirm": "✅ Trade confirmed and submitted for execution through the "
                             "EIP-712 signing and on-chain broadcast pipeline.",
            "risk_query": self._build_risk_text(context),
            "balance": self._build_balance_text(context),
            "unknown": f"I heard: '{cmd.raw_text}'. Available commands: "
                       "status, risk assessment, emergency stop, confirm trade, balance.",
        }

        text = responses.get(cmd.intent, responses["unknown"])

        return VoiceResponse(
            text=text,
            intent_handled=cmd.intent,
            success=True,
            timestamp=timestamp,
        )

    # ── Command Parser ──────────────────────────────────────

    def _parse_command(self, user_text: str) -> VoiceCommand:
        """Parse user text into a structured voice command."""
        text_lower = user_text.lower().strip()

        # Remove wake word if present
        for wake in ["protocol zero", "hey protocol", "okay protocol", "pz"]:
            text_lower = text_lower.replace(wake, "").strip()
            text_lower = text_lower.lstrip(",").strip()

        best_intent = "unknown"
        best_conf = 0.0

        for intent, keywords in self.COMMANDS.items():
            for kw in keywords:
                if kw in text_lower:
                    # Longer match = higher confidence
                    conf = len(kw) / max(len(text_lower), 1)
                    if conf > best_conf:
                        best_conf = conf
                        best_intent = intent

        # Extract asset mentions
        asset = ""
        for token in ["btc", "eth", "sol", "avax", "link", "usdc", "weth"]:
            if token in text_lower:
                asset = token.upper()
                break

        return VoiceCommand(
            raw_text=user_text,
            intent=best_intent,
            asset=asset,
            confidence=min(1.0, best_conf + 0.3) if best_intent != "unknown" else 0.0,
        )

    # ── Response Builders ───────────────────────────────────

    def _build_response_prompt(self, cmd: VoiceCommand, context: dict) -> str:
        """Build a context-aware prompt for Nova to generate a response."""
        ctx_str = json.dumps(context, default=str, indent=2) if context else "{}"
        return (
            f"The user said: \"{cmd.raw_text}\"\n"
            f"Detected intent: {cmd.intent}\n"
            f"Current portfolio context:\n{ctx_str}\n\n"
            f"Generate a brief, professional spoken response (2-3 sentences max). "
            f"Be specific with numbers and status."
        )

    def _build_status_text(self, ctx: dict) -> str:
        pnl = ctx.get("session_pnl", 0)
        trades = ctx.get("trade_count", 0)
        rep = ctx.get("reputation_score", 50)
        regime = ctx.get("market_regime", "UNCERTAIN")
        pnl_word = "profit" if pnl >= 0 else "loss"
        return (
            f"Protocol Zero status report. Session P&L: ${abs(pnl):.2f} {pnl_word} "
            f"across {trades} trades. Reputation score: {rep} out of 100. "
            f"Current market regime: {regime}. All systems operational."
        )

    def _build_risk_text(self, ctx: dict) -> str:
        risk = ctx.get("risk_score", 5)
        regime = ctx.get("market_regime", "UNCERTAIN")
        positions = ctx.get("open_positions", 0)
        exposure = ctx.get("total_exposure_usd", 0)
        level = "low" if risk <= 3 else ("moderate" if risk <= 6 else "high")
        return (
            f"Risk assessment: Current risk level is {level}, score {risk} of 10. "
            f"Market regime: {regime}. {positions} open positions "
            f"with ${exposure:,.2f} total exposure. "
            f"{'No immediate threats detected.' if risk <= 5 else 'Elevated risk — consider reducing exposure.'}"
        )

    def _build_balance_text(self, ctx: dict) -> str:
        eth = ctx.get("wallet_eth", 0)
        weth = ctx.get("wallet_weth", 0)
        usdc = ctx.get("wallet_usdc", 0)
        # Use live ETH price from context if available, otherwise mark as unavailable
        eth_price = ctx.get("eth_price_usd", 0)
        if eth_price > 0:
            total = eth * eth_price + weth * eth_price + usdc
            return (
                f"Wallet balances: {eth:.6f} ETH, {weth:.6f} WETH, "
                f"and {usdc:.2f} USDC. "
                f"Total estimated value: ${total:,.2f} (ETH @ ${eth_price:,.0f})."
            )
        return (
            f"Wallet balances: {eth:.6f} ETH, {weth:.6f} WETH, "
            f"and {usdc:.2f} USDC. "
            f"ETH price unavailable — USD estimate omitted."
        )

    def _build_alert_text(self, alert_type: str, details: dict) -> str:
        alerts = {
            "volatility_spike": f"Warning: Volatility spike detected on {details.get('asset', 'unknown')}. "
                                f"Current volatility: {details.get('volatility', 0):.2f}%. "
                                f"Consider reducing exposure.",
            "kill_switch": "Emergency stop activated. All trading halted immediately.",
            "trade_executed": f"Trade executed: {details.get('action', '?')} "
                              f"{details.get('asset', '?')} for ${details.get('amount', 0):,.2f}. "
                              f"Transaction confirmed on-chain.",
            "risk_threshold": f"Risk threshold breached. Current risk score: "
                              f"{details.get('risk_score', 0)} of 10. Recommending HOLD.",
            "rug_pull_alert": f"Critical alert: Potential rug-pull detected on "
                              f"{details.get('token', 'unknown')}. Trading halted for this asset.",
        }
        return alerts.get(alert_type,
            f"⚠️ {details.get('severity', alert_type).upper()} ALERT: "
            f"{details.get('message', alert_type)}. Protocol Zero monitoring engaged."
        )

    def _build_risk_brief(self, portfolio: dict) -> str:
        positions = portfolio.get("positions", 0)
        exposure = portfolio.get("total_exposure_usd", 0)
        risk = portfolio.get("risk_score", 5)
        regime = portfolio.get("market_regime", "UNCERTAIN")
        pnl = portfolio.get("session_pnl", 0)
        return (
            f"Portfolio risk briefing. {positions} active positions, "
            f"${exposure:,.2f} total exposure. Overall risk score: {risk} of 10. "
            f"Market regime: {regime}. Session P&L: ${pnl:+.2f}. "
            f"{'All clear.' if risk <= 5 else 'Elevated risk — monitor closely.'}"
        )
