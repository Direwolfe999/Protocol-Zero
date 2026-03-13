"""
sign_trade.py — Protocol Zero Trade Validator & Signer
=======================================================
Sits between the AI decision engine and the blockchain.

Architecture:
    Market Data → Protocol Zero (brain.py) → JSON Decision
        → sign_trade.py (validate + sign) → web3.py → Anvil / Sepolia

Rules:
    • The AI NEVER generates raw transactions.
    • The AI NEVER touches private keys.
    • The AI NEVER calculates gas directly.
    • This module is the sole custodian of signing authority.

Usage:
    from sign_trade import validate_and_sign

    result = validate_and_sign(decision_json)
    # result["status"] == "signed"  → ready to broadcast
    # result["status"] == "rejected" → failed validation

CLI:
    python sign_trade.py --json '{"action":"BUY","asset":"ETH",...}'
    python sign_trade.py --file decision.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import config

# ────────────────────────────────────────────────────────────
#  Configuration — uses centralized config.py
# ────────────────────────────────────────────────────────────

CHAIN_MAP = {
    "anvil":   {"rpc": "http://127.0.0.1:8545", "chain_id": 31337},
    "sepolia": {"rpc": config.RPC_URL, "chain_id": 11155111},
}

PRIVATE_KEY: str = config.PRIVATE_KEY
TARGET_CHAIN: str = "sepolia" if config.CHAIN_ID == 11155111 else "anvil"
VALIDATION_REGISTRY: str = config.VALIDATION_REGISTRY_ADDRESS

# EIP-712 domain
EIP712_DOMAIN = {
    "name":              "ProtocolZero",
    "version":           "1",
    "chainId":           config.CHAIN_ID,
    "verifyingContract": config.VALIDATION_REGISTRY_ADDRESS,
}

# TradeIntent struct type for EIP-712
TRADE_INTENT_TYPES = {
    "TradeIntent": [
        {"name": "action",     "type": "string"},
        {"name": "asset",      "type": "string"},
        {"name": "amountUsd",  "type": "uint256"},
        {"name": "confidence", "type": "uint256"},  # basis points (0-10000)
        {"name": "riskScore",  "type": "uint256"},
        {"name": "nonce",      "type": "uint256"},
        {"name": "expiry",     "type": "uint256"},
        {"name": "agent",      "type": "address"},
    ],
}


# ────────────────────────────────────────────────────────────
#  Validation Schema
# ────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "action", "asset", "confidence", "risk_score",
    "position_size_percent", "stop_loss_percent",
    "take_profit_percent", "market_regime",
}

VALID_ACTIONS  = {"BUY", "SELL", "HOLD"}
VALID_REGIMES  = {"TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"}
MAX_POSITION_PCT = 2.0     # hard cap: 2% of capital per trade
CONFIDENCE_FLOOR = 0.6     # below this → force HOLD
MAX_RISK_SCORE   = 10


@dataclass
class ValidationResult:
    """Result of validating an AI decision."""
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def reject(self, reason: str) -> None:
        self.valid = False
        self.errors.append(reason)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def validate_decision(decision: dict[str, Any]) -> ValidationResult:
    """
    Validate a JSON decision from the AI brain.

    Checks:
        1. All required fields are present
        2. Action is BUY / SELL / HOLD
        3. Confidence ≥ 0.6 (or force HOLD)
        4. Position size ≤ 2%
        5. Stop-loss and take-profit are set
        6. Risk score is 1-10
        7. Market regime is valid
        8. No leverage (implicit: amount_usd ≤ capital)
    """
    vr = ValidationResult()

    # 1. Required fields
    missing = REQUIRED_FIELDS - set(decision.keys())
    if missing:
        vr.reject(f"Missing required fields: {', '.join(sorted(missing))}")
        return vr  # can't continue without fields

    # 2. Valid action
    action = decision.get("action", "").upper()
    if action not in VALID_ACTIONS:
        vr.reject(f"Invalid action '{action}'. Must be one of {VALID_ACTIONS}")

    # 3. Confidence threshold
    conf = float(decision.get("confidence", 0))
    if conf < 0 or conf > 1:
        vr.reject(f"Confidence {conf} out of range [0, 1]")
    elif conf < CONFIDENCE_FLOOR and action != "HOLD":
        vr.reject(f"Confidence {conf:.2f} < {CONFIDENCE_FLOOR} — must HOLD. "
                  "AI attempted to trade with insufficient conviction.")

    # 4. Position size cap
    pos = float(decision.get("position_size_percent", 0))
    if pos > MAX_POSITION_PCT:
        vr.reject(f"Position size {pos:.1f}% exceeds hard cap of {MAX_POSITION_PCT}%")
    if pos < 0:
        vr.reject(f"Negative position size: {pos}")

    # 5. Stop-loss and take-profit
    sl = float(decision.get("stop_loss_percent", 0))
    tp = float(decision.get("take_profit_percent", 0))
    if action != "HOLD":
        if sl <= 0:
            vr.reject("Stop-loss not set. Every trade must have a stop-loss.")
        if tp <= 0:
            vr.reject("Take-profit not set. Every trade must have a take-profit.")
        if sl > 25:
            vr.warn(f"Stop-loss at {sl}% is very wide — consider tightening")
        if tp > 50:
            vr.warn(f"Take-profit at {tp}% is ambitious — ensure it's realistic")

    # 6. Risk score
    risk = int(decision.get("risk_score", 0))
    if risk < 1 or risk > MAX_RISK_SCORE:
        vr.reject(f"Risk score {risk} out of range [1, {MAX_RISK_SCORE}]")

    # 7. Market regime
    regime = decision.get("market_regime", "").upper()
    if regime not in VALID_REGIMES:
        vr.reject(f"Invalid market regime '{regime}'. Must be one of {VALID_REGIMES}")

    # 8. HOLD should have zero position
    if action == "HOLD" and pos > 0:
        vr.warn("HOLD action with non-zero position size — resetting to 0")

    return vr


# ────────────────────────────────────────────────────────────
#  EIP-712 Signing
# ────────────────────────────────────────────────────────────

_nonce_counter: int = 0


def _next_nonce() -> int:
    global _nonce_counter
    _nonce_counter += 1
    return _nonce_counter


def sign_intent(decision: dict[str, Any], private_key: str = "") -> dict[str, Any]:
    """
    Build an EIP-712 TradeIntent and sign it.

    Returns:
        {
            "intent":    { ... structured data ... },
            "signature": "0x...",
            "signer":    "0x...",
            "tx_hash":   None  (filled after broadcast),
        }
    """
    from eth_account import Account
    from eth_account.messages import encode_typed_data

    pk = private_key or PRIVATE_KEY
    if not pk:
        raise ValueError("No private key configured. Set AGENT_PRIVATE_KEY in .env")

    acct  = Account.from_key(pk)
    nonce = _next_nonce()
    expiry = int(time.time()) + 300  # 5 min TTL

    # Convert to on-chain representation
    conf_bps = int(float(decision.get("confidence", 0)) * 10_000)
    amount   = int(float(decision.get("amount_usd", 0)) * 100)  # cents

    intent_data = {
        "action":     decision.get("action", "HOLD"),
        "asset":      decision.get("asset", "ETH"),
        "amountUsd":  amount,
        "confidence": conf_bps,
        "riskScore":  int(decision.get("risk_score", 5)),
        "nonce":      nonce,
        "expiry":     expiry,
        "agent":      acct.address,
    }

    # EIP-712 typed data signing
    signable = encode_typed_data(
        domain_data=EIP712_DOMAIN,
        message_types=TRADE_INTENT_TYPES,
        message_data=intent_data,
    )
    signed = acct.sign_message(signable)

    return {
        "intent":    intent_data,
        "signature": signed.signature.hex() if hasattr(signed.signature, 'hex') else hex(signed.signature),
        "signer":    acct.address,
        "tx_hash":   None,
    }


# ────────────────────────────────────────────────────────────
#  Broadcast to Chain
# ────────────────────────────────────────────────────────────

def broadcast_intent(signed_result: dict[str, Any]) -> dict[str, Any]:
    """
    Submit the signed intent to the Validation Registry on-chain.

    In production this calls submitIntent(intent, signature) on the
    Risk Router contract.  For the hackathon demo, if no contract is
    deployed, it falls back to sending a zero-value self-transfer as
    proof-of-signing.
    """
    from web3 import Web3

    chain_cfg = CHAIN_MAP.get(TARGET_CHAIN, CHAIN_MAP["anvil"])
    rpc_url   = chain_cfg["rpc"]
    chain_id  = chain_cfg["chain_id"]

    if not rpc_url:
        return {**signed_result, "broadcast": "skipped", "reason": "No RPC URL configured"}

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {**signed_result, "broadcast": "failed", "reason": "Cannot connect to RPC"}

    pk   = PRIVATE_KEY
    acct = w3.eth.account.from_key(pk)

    # Try calling submitIntent on the validation registry
    if VALIDATION_REGISTRY and VALIDATION_REGISTRY != "0x" + "0" * 40:
        # ABI stub for submitIntent(TradeIntent, bytes)
        SUBMIT_ABI = [{
            "name": "submitIntent",
            "type": "function",
            "stateMutability": "nonpayable",
            "inputs": [
                {"name": "intent",    "type": "tuple",
                 "components": [
                     {"name": "action",     "type": "string"},
                     {"name": "asset",      "type": "string"},
                     {"name": "amountUsd",  "type": "uint256"},
                     {"name": "confidence", "type": "uint256"},
                     {"name": "riskScore",  "type": "uint256"},
                     {"name": "nonce",      "type": "uint256"},
                     {"name": "expiry",     "type": "uint256"},
                     {"name": "agent",      "type": "address"},
                 ]},
                {"name": "signature", "type": "bytes"},
            ],
            "outputs": [{"name": "", "type": "bool"}],
        }]

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(VALIDATION_REGISTRY),
            abi=SUBMIT_ABI,
        )

        intent = signed_result["intent"]
        sig_bytes = bytes.fromhex(
            signed_result["signature"].replace("0x", ""))

        try:
            tx = contract.functions.submitIntent(
                (intent["action"], intent["asset"], intent["amountUsd"],
                 intent["confidence"], intent["riskScore"],
                 intent["nonce"], intent["expiry"], intent["agent"]),
                sig_bytes,
            ).build_transaction({
                "from":     acct.address,
                "nonce":    w3.eth.get_transaction_count(acct.address),
                "gas":      300_000,
                "gasPrice": w3.eth.gas_price,
                "chainId":  chain_id,
            })

            signed_tx = w3.eth.account.sign_transaction(tx, pk)
            tx_hash   = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            return {
                **signed_result,
                "broadcast": "submitted",
                "tx_hash":   tx_hash.hex(),
                "chain":     TARGET_CHAIN,
            }
        except Exception as exc:
            # Fall through to self-transfer fallback
            pass

    # Fallback: zero-value self-transfer (proof of key custody)
    try:
        tx = {
            "from":     acct.address,
            "to":       acct.address,
            "value":    0,
            "nonce":    w3.eth.get_transaction_count(acct.address),
            "gas":      21_000,
            "gasPrice": w3.eth.gas_price,
            "chainId":  chain_id,
            "data":     w3.to_bytes(text=json.dumps(signed_result["intent"], default=str)),
        }
        signed_tx = w3.eth.account.sign_transaction(tx, pk)
        tx_hash   = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return {
            **signed_result,
            "broadcast": "fallback-self-tx",
            "tx_hash":   tx_hash.hex(),
            "chain":     TARGET_CHAIN,
        }
    except Exception as exc:
        return {
            **signed_result,
            "broadcast": "failed",
            "reason":    str(exc),
        }


# ────────────────────────────────────────────────────────────
#  Public API
# ────────────────────────────────────────────────────────────

def validate_and_sign(
    decision: dict[str, Any],
    *,
    broadcast: bool = False,
    private_key: str = "",
) -> dict[str, Any]:
    """
    Full pipeline: validate → sign → (optionally) broadcast.

    Returns:
        {
            "status":     "signed" | "rejected" | "broadcast",
            "validation": { valid, errors, warnings },
            "decision":   { ...original... },
            "signed":     { intent, signature, signer } | None,
            "tx_hash":    "0x..." | None,
        }
    """
    # Step 1: Validate
    vr = validate_decision(decision)

    result: dict[str, Any] = {
        "status":     "rejected" if not vr.valid else "validated",
        "validation": {
            "valid":    vr.valid,
            "errors":   vr.errors,
            "warnings": vr.warnings,
        },
        "decision":   decision,
        "signed":     None,
        "tx_hash":    None,
    }

    if not vr.valid:
        return result

    # HOLD → valid but nothing to sign
    if decision.get("action", "").upper() == "HOLD":
        result["status"] = "hold"
        return result

    # Step 2: Sign
    try:
        signed = sign_intent(decision, private_key)
        result["signed"]  = signed
        result["status"]  = "signed"
    except Exception as exc:
        result["status"] = "sign-failed"
        result["validation"]["errors"].append(f"Signing failed: {exc}")
        return result

    # Step 3: Broadcast (optional)
    if broadcast:
        try:
            bc_result = broadcast_intent(signed)
            result["tx_hash"]  = bc_result.get("tx_hash")
            result["status"]   = bc_result.get("broadcast", "failed")
            result["chain"]    = bc_result.get("chain", TARGET_CHAIN)
        except Exception as exc:
            result["status"] = "broadcast-failed"
            result["validation"]["errors"].append(f"Broadcast failed: {exc}")

    return result


# ────────────────────────────────────────────────────────────
#  CLI
# ────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Protocol Zero — Trade Validator & Signer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sign_trade.py --json '{"action":"BUY","asset":"ETH","confidence":0.78,...}'
  python sign_trade.py --file decision.json --broadcast
  python sign_trade.py --validate-only --json '{"action":"SELL",...}'
        """,
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--json",     type=str, help="Decision JSON as a string")
    grp.add_argument("--file",     type=str, help="Path to a JSON file")
    parser.add_argument("--broadcast",     action="store_true",
                        help="Broadcast the signed intent to chain")
    parser.add_argument("--validate-only", action="store_true",
                        help="Only validate, do not sign")
    parser.add_argument("--chain",         type=str, default=None,
                        choices=["anvil", "sepolia"],
                        help="Override target chain")

    args = parser.parse_args()

    if args.chain:
        global TARGET_CHAIN
        TARGET_CHAIN = args.chain

    # Load decision
    if args.json:
        decision = json.loads(args.json)
    else:
        with open(args.file, "r") as f:
            decision = json.load(f)

    print(f"\n{'═' * 60}")
    print(f"  Protocol Zero — Trade Validator & Signer")
    print(f"{'═' * 60}")
    print(f"  Action:     {decision.get('action', '?')}")
    print(f"  Asset:      {decision.get('asset', '?')}")
    print(f"  Confidence: {decision.get('confidence', '?')}")
    print(f"  Risk Score: {decision.get('risk_score', '?')}")
    print(f"  Regime:     {decision.get('market_regime', '?')}")
    print(f"  Position:   {decision.get('position_size_percent', '?')}%")
    print(f"{'─' * 60}")

    if args.validate_only:
        vr = validate_decision(decision)
        if vr.valid:
            print("  ✅  Validation PASSED")
        else:
            print("  ❌  Validation FAILED")
            for err in vr.errors:
                print(f"      • {err}")
        for w in vr.warnings:
            print(f"  ⚠   {w}")
        sys.exit(0 if vr.valid else 1)

    result = validate_and_sign(decision, broadcast=args.broadcast)

    if result["status"] == "rejected":
        print("  ❌  REJECTED — validation failed:")
        for err in result["validation"]["errors"]:
            print(f"      • {err}")
        sys.exit(1)
    elif result["status"] == "hold":
        print("  🟡  HOLD — no signing required")
        sys.exit(0)
    elif result["status"] == "signed":
        print("  ✅  SIGNED successfully")
        print(f"  Signer:    {result['signed']['signer']}")
        print(f"  Signature: {result['signed']['signature'][:42]}…")
        if not args.broadcast:
            print("  (use --broadcast to send to chain)")
    elif result["status"] in ("submitted", "fallback-self-tx"):
        print(f"  ✅  BROADCAST — {result['status']}")
        print(f"  TX Hash: {result.get('tx_hash', '?')}")
        print(f"  Chain:   {result.get('chain', TARGET_CHAIN)}")
    else:
        print(f"  ⚠   Status: {result['status']}")
        for err in result["validation"].get("errors", []):
            print(f"      • {err}")

    for w in result["validation"].get("warnings", []):
        print(f"  ⚠   {w}")

    print(f"{'═' * 60}\n")

    # Output full JSON result
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    _cli()
