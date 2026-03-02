"""
Protocol Zero — EIP-712 Trade Intent Signer
=============================================
Pure cryptographic module — NO RPC connection required.

This module implements the EIP-712 "Typed Structured Data" standard
(https://eips.ethereum.org/EIPS/eip-712) for signing trade intents
off-chain.  The resulting signature + struct hash are later submitted
to the on-chain Risk Router (Validation Registry) for verification.

EIP-712 Primer
--------------
EIP-712 prevents "blind signing" by encoding data into a human-readable
typed structure before hashing.  The hash is computed as:

    hashStruct(message) = keccak256(typeHash ‖ encodeData(message))
    domainSeparator     = keccak256(typeHash ‖ encodeData(domain))
    digest              = keccak256("\\x19\\x01" ‖ domainSeparator ‖ hashStruct)

The wallet signs this final `digest`.  The smart contract recomputes
the same digest from calldata and calls `ecrecover` to verify.

TradeIntent Struct (hackathon spec)
───────────────────────────────────
    struct TradeIntent {
        string  action;       // "BUY" | "SELL" | "HOLD"
        string  asset;        // Token ticker, e.g. "ETH"
        uint256 amountUsd;    // Trade size in USD cents  (100 = $1.00)
        uint256 confidence;   // Model confidence in bps  (10000 = 100%)
        uint256 nonce;        // Monotonic nonce — replay protection
        uint256 expiry;       // Unix timestamp — intent TTL
        address agent;        // Signing wallet address
    }

Usage
-----
    from eip712_signer import build_and_sign_intent

    order = {"token": "ETH", "amount": 250.0, "direction": "BUY"}
    result = build_and_sign_intent(order, confidence=0.85)

    result["signature"]    # bytes   — 65-byte ECDSA signature
    result["intent_hash"]  # bytes32 — EIP-712 struct hash
    result["message"]      # dict    — raw typed-data message
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

import config

logger = logging.getLogger("protocol_zero.eip712")


# ════════════════════════════════════════════════════════════
#  Constants
# ════════════════════════════════════════════════════════════

# Intent signatures expire after this many seconds (5 minutes default).
DEFAULT_INTENT_TTL_SECONDS: int = 300

# Directions the agent may express
VALID_DIRECTIONS: set[str] = {"BUY", "SELL", "HOLD"}


# ════════════════════════════════════════════════════════════
#  EIP-712 Domain — ties signatures to ONE chain + contract
# ════════════════════════════════════════════════════════════

def get_domain() -> dict[str, Any]:
    """
    Return the EIP-712 domain separator parameters.

    These MUST match the values hard-coded in the Validation Registry
    (Risk Router) contract, otherwise `ecrecover` will return the
    wrong signer and the intent will be rejected.
    """
    return {
        "name":              "ProtocolZero",
        "version":           "1",
        "chainId":           config.CHAIN_ID,
        "verifyingContract": Web3.to_checksum_address(
            config.VALIDATION_REGISTRY_ADDRESS
        ),
    }


# ════════════════════════════════════════════════════════════
#  EIP-712 Type Definitions
# ════════════════════════════════════════════════════════════

# This dict maps Solidity struct names → ordered field lists.
# Order matters: it determines the typeHash.
TRADE_INTENT_TYPES: dict[str, list[dict[str, str]]] = {
    "TradeIntent": [
        {"name": "action",     "type": "string"},
        {"name": "asset",      "type": "string"},
        {"name": "amountUsd",  "type": "uint256"},
        {"name": "confidence", "type": "uint256"},
        {"name": "nonce",      "type": "uint256"},
        {"name": "expiry",     "type": "uint256"},
        {"name": "agent",      "type": "address"},
    ],
}

PRIMARY_TYPE: str = "TradeIntent"


# ════════════════════════════════════════════════════════════
#  Nonce Manager (in-memory, per-process)
# ════════════════════════════════════════════════════════════

@dataclass
class _NonceTracker:
    """
    Simple monotonic nonce to prevent replay attacks.
    In production, persist to disk or read from the contract.
    """
    _current: int = 0

    def next(self) -> int:
        self._current += 1
        return self._current

    @property
    def current(self) -> int:
        return self._current


_nonce_tracker = _NonceTracker()


# ════════════════════════════════════════════════════════════
#  Core: Build Message → Encode → Sign
# ════════════════════════════════════════════════════════════

def build_intent_message(
    order_details: dict,
    confidence: float = 0.5,
    ttl_seconds: int = DEFAULT_INTENT_TTL_SECONDS,
) -> dict[str, Any]:
    """
    Construct the EIP-712 message payload from plain order details.

    Parameters
    ----------
    order_details : dict
        Required keys:
            token     : str    — e.g. "ETH", "BTC"
            amount    : float  — trade size in USD
            direction : str    — "BUY", "SELL", or "HOLD"
    confidence : float
        Model confidence 0.0 – 1.0.
    ttl_seconds : int
        How many seconds until the signed intent expires.

    Returns
    -------
    dict — the fully populated TradeIntent message fields.
    """
    direction = str(order_details.get("direction", "HOLD")).upper()
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"Invalid direction '{direction}'. Must be one of {VALID_DIRECTIONS}"
        )

    token  = str(order_details.get("token", "ETH")).upper()
    amount = float(order_details.get("amount", 0))

    # Derive the agent address from the loaded private key
    account = Account.from_key(config.PRIVATE_KEY)

    message: dict[str, Any] = {
        "action":     direction,
        "asset":      token,
        "amountUsd":  int(amount * 100),              # → USD cents
        "confidence": int(confidence * 10_000),        # → basis points
        "nonce":      _nonce_tracker.next(),
        "expiry":     int(time.time()) + ttl_seconds,
        "agent":      account.address,
    }

    logger.debug("Built intent message: %s", message)
    return message


def sign_intent(message: dict[str, Any]) -> dict[str, Any]:
    """
    EIP-712-sign a TradeIntent message with the bot's private key.

    Parameters
    ----------
    message : dict
        Output of `build_intent_message()`.

    Returns
    -------
    dict with keys:
        signature    : bytes   — 65-byte ECDSA signature (r‖s‖v)
        intent_hash  : bytes   — 32-byte EIP-712 struct hash
        signer       : str     — checksummed signer address
        message      : dict    — echo of the signed message
    """
    domain = get_domain()

    # ── Encode the typed data for signing ─────────────────
    #    encode_typed_data(domain, types, primaryType, message)
    signable = encode_typed_data(
        domain,
        TRADE_INTENT_TYPES,
        PRIMARY_TYPE,
        message,
    )

    # ── Sign with the agent's private key ─────────────────
    account = Account.from_key(config.PRIVATE_KEY)
    signed  = account.sign_message(signable)

    result = {
        "signature":   signed.signature,          # bytes, 65 bytes
        "intent_hash": signable.body,             # bytes32 struct hash
        "signer":      account.address,
        "message":     message,
    }

    logger.info(
        "🔏  Signed TradeIntent  |  %s %s  $%.2f  nonce=%d  expiry=%d",
        message["action"],
        message["asset"],
        message["amountUsd"] / 100,
        message["nonce"],
        message["expiry"],
    )
    return result


# ════════════════════════════════════════════════════════════
#  Convenience: one-call build + sign
# ════════════════════════════════════════════════════════════

def build_and_sign_intent(
    order_details: dict,
    confidence: float = 0.5,
    ttl_seconds: int = DEFAULT_INTENT_TTL_SECONDS,
) -> dict[str, Any]:
    """
    All-in-one helper: build the intent message, then sign it.

    Parameters
    ----------
    order_details : dict   — { token, amount, direction }
    confidence    : float  — model confidence 0.0–1.0
    ttl_seconds   : int    — signature validity window

    Returns
    -------
    dict — same structure as `sign_intent()`.
    """
    message = build_intent_message(order_details, confidence, ttl_seconds)
    return sign_intent(message)


# ════════════════════════════════════════════════════════════
#  Verification helper (useful for local tests & debugging)
# ════════════════════════════════════════════════════════════

def recover_signer(
    message: dict[str, Any],
    signature: bytes,
) -> str:
    """
    Recover the signer address from a signature + message.
    This mirrors what the Risk Router contract does on-chain
    with `ecrecover`.

    Returns
    -------
    str — checksummed Ethereum address of the signer.
    """
    domain = get_domain()

    signable = encode_typed_data(
        domain,
        TRADE_INTENT_TYPES,
        PRIMARY_TYPE,
        message,
    )

    recovered = Account.recover_message(signable, signature=signature)
    logger.debug("Recovered signer: %s", recovered)
    return recovered


# ════════════════════════════════════════════════════════════
#  CLI Smoke Test
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    sample_order = {
        "token": "ETH",
        "amount": 150.00,
        "direction": "BUY",
    }

    print("─" * 60)
    print("  Protocol Zero — EIP-712 Signer Smoke Test")
    print("─" * 60)

    result = build_and_sign_intent(sample_order, confidence=0.82)

    print(f"  Signer       : {result['signer']}")
    print(f"  Action       : {result['message']['action']}")
    print(f"  Asset        : {result['message']['asset']}")
    print(f"  Amount (¢)   : {result['message']['amountUsd']}")
    print(f"  Confidence   : {result['message']['confidence']} bps")
    print(f"  Nonce        : {result['message']['nonce']}")
    print(f"  Expiry       : {result['message']['expiry']}")
    print(f"  Signature    : 0x{result['signature'].hex()}")
    print(f"  Intent Hash  : 0x{result['intent_hash'].hex()}")

    # Verify round-trip
    recovered = recover_signer(result["message"], result["signature"])
    assert recovered == result["signer"], "Signature verification FAILED"
    print(f"\n  ✅ Signature verified — recovered {recovered}")
