"""
Protocol Zero — Validation Artifacts Builder
===============================================
Creates cryptographically-sealed validation artifacts for the
ERC-8004 Validation Registry.

A Validation Artifact bundles:
  1. Market snapshot (price, volume, indicators at decision time)
  2. AI reasoning trace (full brain output + confidence)
  3. Risk check results (all 6 checks with pass/fail)
  4. EIP-712 signed intent (signature + struct hash)
  5. Performance context (current Sharpe, drawdown, win rate)

The artifact is:
  - Hashed with keccak256 → requestHash
  - Stored as JSON → requestURI (IPFS or local)
  - Submitted to Validation Registry via validationRequest()

This creates a full audit trail for every trade decision,
proving the agent's reasoning was sound BEFORE execution.

Usage:
    from validation_artifacts import ValidationArtifactBuilder

    builder = ValidationArtifactBuilder(chain_interactor)
    artifact = builder.build_artifact(decision, market_data, risk_results, signed_intent)
    builder.submit_to_registry(artifact)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from web3 import Web3

import config

logger = logging.getLogger("protocol_zero.validation")

# Local artifact storage
_ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
_ARTIFACTS_DIR.mkdir(exist_ok=True)


@dataclass
class ValidationArtifact:
    """Complete validation artifact for a trade decision."""
    artifact_id: str
    timestamp: str
    agent_address: str
    chain_id: int

    # Market context
    market_snapshot: dict[str, Any]

    # AI decision
    decision: dict[str, Any]
    reasoning_trace: str

    # Risk assessment
    risk_checks: list[dict[str, Any]]
    risk_passed: bool

    # Signed intent
    signature: str = ""
    intent_hash: str = ""

    # Performance context
    performance_metrics: dict[str, Any] = field(default_factory=dict)

    # Hashes
    artifact_hash: str = ""
    request_uri: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "schemaVersion": "erc8004-validation-v1",
            "artifactId": self.artifact_id,
            "timestamp": self.timestamp,
            "agentAddress": self.agent_address,
            "chainId": self.chain_id,
            "marketSnapshot": self.market_snapshot,
            "decision": self.decision,
            "reasoningTrace": self.reasoning_trace,
            "riskAssessment": {
                "passed": self.risk_passed,
                "checks": self.risk_checks,
            },
            "signedIntent": {
                "signature": self.signature,
                "intentHash": self.intent_hash,
            },
            "performanceMetrics": self.performance_metrics,
            "artifactHash": self.artifact_hash,
        }

    def to_json(self) -> str:
        """Canonical JSON serialization (sorted keys)."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)


class ValidationArtifactBuilder:
    """
    Builds, hashes, stores, and submits validation artifacts
    for every trade decision.

    Maintains a **Merkle tree** of artifact hashes so the complete
    audit trail is tamper-evident: modifying any historical artifact
    changes the Merkle root, making tampering immediately detectable.
    """

    def __init__(self, chain_interactor: Any = None) -> None:
        """
        Parameters
        ----------
        chain_interactor : ChainInteractor instance (optional).
            If provided, artifacts will be submitted on-chain.
        """
        self.chain = chain_interactor
        self._artifact_count = 0
        self._merkle_leaves: list[str] = []  # ordered artifact hashes
        self._merkle_root: str = "0x" + "0" * 64  # genesis root

    def build_artifact(
        self,
        decision: dict[str, Any],
        market_data: Any = None,
        risk_results: tuple[bool, list[str]] | None = None,
        signed_intent: dict[str, Any] | None = None,
        performance_report: dict[str, Any] | None = None,
    ) -> ValidationArtifact:
        """
        Build a complete validation artifact from all pipeline outputs.

        Parameters
        ----------
        decision          : AI brain output (action, asset, confidence, etc.)
        market_data       : DataFrame or dict of market conditions
        risk_results      : (passed, messages) from run_all_checks()
        signed_intent     : Output from sign_trade.validate_and_sign()
        performance_report: Output from PerformanceTracker.get_report()
        """
        self._artifact_count += 1
        now = datetime.now(timezone.utc)
        artifact_id = f"pz-{now.strftime('%Y%m%d%H%M%S')}-{self._artifact_count:04d}"

        # Resolve agent address
        agent_address = "0x0000000000000000000000000000000000000000"
        if self.chain:
            agent_address = self.chain.address

        # Build market snapshot
        market_snapshot = self._build_market_snapshot(market_data)

        # Build risk check results
        risk_passed = True
        risk_checks = []
        if risk_results:
            risk_passed, messages = risk_results
            for msg in messages:
                passed = msg.startswith("✅")
                risk_checks.append({
                    "check": msg.split(": ", 1)[0].lstrip("✅❌ ").strip(),
                    "passed": passed,
                    "detail": msg.split(": ", 1)[-1] if ": " in msg else msg,
                })

        # Extract signature info
        signature = ""
        intent_hash = ""
        if signed_intent:
            sig_data = signed_intent.get("signed", {})
            if sig_data:
                signature = sig_data.get("signature", "")
                intent_data = sig_data.get("intent", {})
                intent_hash = json.dumps(intent_data, sort_keys=True)

        artifact = ValidationArtifact(
            artifact_id=artifact_id,
            timestamp=now.isoformat(),
            agent_address=agent_address,
            chain_id=config.CHAIN_ID,
            market_snapshot=market_snapshot,
            decision={
                "action": decision.get("action", "HOLD"),
                "asset": decision.get("asset", ""),
                "confidence": decision.get("confidence", 0),
                "risk_score": decision.get("risk_score", 5),
                "position_size_percent": decision.get("position_size_percent", 0),
                "market_regime": decision.get("market_regime", "UNCERTAIN"),
                "amount_usd": decision.get("amount_usd", 0),
            },
            reasoning_trace=decision.get("reason", decision.get("entry_reasoning", "")),
            risk_checks=risk_checks,
            risk_passed=risk_passed,
            signature=signature,
            intent_hash=intent_hash,
            performance_metrics=performance_report or {},
        )

        # Compute artifact hash
        artifact.artifact_hash = self._compute_hash(artifact)

        # Chain into Merkle tree
        self._merkle_leaves.append(artifact.artifact_hash)
        self._merkle_root = self._compute_merkle_root(self._merkle_leaves)

        # Save locally
        artifact.request_uri = self._save_artifact(artifact)

        logger.info(
            "📋 Built validation artifact %s | hash=%s | merkle_root=%s",
            artifact_id, artifact.artifact_hash[:18] + "…",
            self._merkle_root[:18] + "…",
        )
        return artifact

    def _build_market_snapshot(self, market_data: Any) -> dict[str, Any]:
        """Extract a compact market snapshot from DataFrame or dict."""
        if market_data is None:
            return {"status": "unavailable"}

        try:
            import pandas as pd
            if isinstance(market_data, pd.DataFrame) and len(market_data) > 0:
                latest = market_data.iloc[-1]
                return {
                    "timestamp": str(latest.get("timestamp", "")),
                    "price": float(latest.get("close", 0)),
                    "open": float(latest.get("open", 0)),
                    "high": float(latest.get("high", 0)),
                    "low": float(latest.get("low", 0)),
                    "volume": float(latest.get("volume", 0)),
                    "sma_12": float(latest.get("sma_12", 0)) if pd.notna(latest.get("sma_12")) else None,
                    "sma_26": float(latest.get("sma_26", 0)) if pd.notna(latest.get("sma_26")) else None,
                    "rsi_14": float(latest.get("rsi_14", 0)) if pd.notna(latest.get("rsi_14")) else None,
                    "pct_change": float(latest.get("pct_change", 0)) if pd.notna(latest.get("pct_change")) else None,
                    "candles_analyzed": len(market_data),
                }
        except Exception:
            pass

        if isinstance(market_data, dict):
            return market_data

        return {"status": "unparseable"}

    def _compute_hash(self, artifact: ValidationArtifact) -> str:
        """Compute keccak256 hash of the artifact (excluding the hash field itself)."""
        data = artifact.to_dict()
        data.pop("artifactHash", None)
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        raw_hash = Web3.keccak(text=canonical)
        return "0x" + raw_hash.hex()

    def _save_artifact(self, artifact: ValidationArtifact) -> str:
        """Save artifact to local JSON file."""
        filepath = _ARTIFACTS_DIR / f"{artifact.artifact_id}.json"
        try:
            filepath.write_text(artifact.to_json(), encoding="utf-8")
            logger.debug("💾 Artifact saved to %s", filepath)
        except OSError as exc:
            logger.error("Failed to save artifact %s: %s", artifact.artifact_id, exc)
        return str(filepath)

    def submit_to_registry(
        self,
        artifact: ValidationArtifact,
        validator_address: str | None = None,
    ) -> str | None:
        """
        Submit the validation artifact to the on-chain Validation Registry
        using ERC-8004's validationRequest().

        Parameters
        ----------
        artifact          : The built ValidationArtifact
        validator_address : Address of the validator contract. Defaults to
                           the Validation Registry address from config.

        Returns
        -------
        str | None — Transaction hash if submitted, None if skipped.
        """
        if not self.chain:
            logger.warning("No chain interactor — skipping on-chain submission.")
            return None

        try:
            target_validator = validator_address or config.VALIDATION_REGISTRY_ADDRESS

            # Get agent's token ID from Identity Registry
            agent_id = 0
            try:
                agent_id = self.chain.get_token_id()
            except Exception:
                logger.warning("Could not get agent token ID — using 0")

            request_uri = artifact.request_uri
            request_hash = bytes.fromhex(artifact.artifact_hash[2:])  # strip 0x

            tx_hash = self.chain.submit_validation_request(
                validator_address=target_validator,
                agent_id=agent_id,
                request_uri=request_uri,
                request_hash=request_hash,
            )
            logger.info("📤 Validation request submitted — TX: %s", tx_hash)
            return tx_hash

        except Exception as exc:
            logger.error("Validation submission failed: %s", exc)
            return None

    def get_artifact_history(self, limit: int = 50) -> list[dict]:
        """Load recent artifacts from disk."""
        artifacts = []
        for filepath in sorted(_ARTIFACTS_DIR.glob("pz-*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                artifacts.append(data)
            except Exception:
                continue
        return artifacts

    # ── Merkle Tree ─────────────────────────────────────────

    @staticmethod
    def _compute_merkle_root(leaves: list[str]) -> str:
        """
        Compute the Merkle root of an ordered list of artifact hashes.

        Each leaf is an ``0x``-prefixed keccak256 hex string.  Pairs are
        concatenated in sorted order and re-hashed until a single root
        remains.  This makes the entire audit trail tamper-evident.
        """
        if not leaves:
            return "0x" + "0" * 64

        # Convert hex strings to bytes
        layer = [bytes.fromhex(h[2:]) if h.startswith("0x") else bytes.fromhex(h) for h in leaves]

        while len(layer) > 1:
            next_layer: list[bytes] = []
            for i in range(0, len(layer), 2):
                if i + 1 < len(layer):
                    # Sort pair for deterministic ordering
                    pair = sorted([layer[i], layer[i + 1]])
                    combined = pair[0] + pair[1]
                else:
                    # Odd leaf — promote unpaired
                    combined = layer[i] + layer[i]
                next_layer.append(Web3.keccak(combined))
            layer = next_layer

        return "0x" + layer[0].hex()

    @property
    def merkle_root(self) -> str:
        """Current Merkle root of all chained artifacts."""
        return self._merkle_root

    @property
    def artifact_count(self) -> int:
        """Number of artifacts in the chain."""
        return len(self._merkle_leaves)

    def verify_artifact(self, artifact_path: str) -> bool:
        """Verify an artifact's hash matches its content."""
        try:
            filepath = Path(artifact_path)
            data = json.loads(filepath.read_text(encoding="utf-8"))
            stored_hash = data.pop("artifactHash", "")

            canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
            computed_hash = "0x" + Web3.keccak(text=canonical).hex()

            if stored_hash == computed_hash:
                logger.info("✅ Artifact hash verified: %s", computed_hash[:18] + "…")
                return True
            else:
                logger.warning(
                    "❌ Hash mismatch! Stored=%s Computed=%s",
                    stored_hash[:18], computed_hash[:18],
                )
                return False
        except Exception as exc:
            logger.error("Verification failed: %s", exc)
            return False


# ════════════════════════════════════════════════════════════
#  CLI Smoke Test
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("─" * 55)
    print("  Protocol Zero — Validation Artifacts Smoke Test")
    print("─" * 55)

    builder = ValidationArtifactBuilder()

    test_decision = {
        "action": "BUY",
        "asset": "ETH",
        "amount_usd": 250.0,
        "confidence": 0.82,
        "risk_score": 4,
        "position_size_percent": 1.2,
        "market_regime": "TRENDING",
        "reason": "SMA-12/26 bullish crossover with RSI momentum at 62",
    }

    test_risk = (True, [
        "✅  check_max_position_size: Position size OK",
        "✅  check_daily_loss_limit: Daily PnL $+0.00 within limits",
        "✅  check_trade_frequency: Trade frequency OK (0/10 per hour)",
        "✅  check_concentration: Concentration in ETH: 3% OK",
        "✅  check_confidence_floor: Confidence 82% OK",
        "✅  check_intent_expiry: No expiry field — skipping check",
    ])

    artifact = builder.build_artifact(
        decision=test_decision,
        risk_results=test_risk,
    )

    print(f"\n  Artifact ID  : {artifact.artifact_id}")
    print(f"  Hash         : {artifact.artifact_hash}")
    print(f"  Saved to     : {artifact.request_uri}")
    print(f"  Risk Passed  : {artifact.risk_passed}")
    print(f"  Checks       : {len(artifact.risk_checks)}")

    # Verify
    ok = builder.verify_artifact(artifact.request_uri)
    print(f"  Verification : {'✅ PASSED' if ok else '❌ FAILED'}")
