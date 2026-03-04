"""
Protocol Zero — Centralized Configuration
==========================================
Loads every secret / tunable from the .env file exactly once.
Every other module imports from here — never from os.environ directly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ────────────────────────────
_env_path = Path(__file__).resolve().parent / ".env"
if not _env_path.exists():
    print("⛔  .env file not found. Copy .env.example → .env and fill in your keys.")
    sys.exit(1)
load_dotenv(_env_path)


def _require(key: str) -> str:
    """Return an env var or crash early with a clear message."""
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


# ── AWS / Bedrock ───────────────────────────────────────────
AWS_ACCESS_KEY_ID      = _require("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY  = _require("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION     = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BEDROCK_MODEL_ID       = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")

# ── Blockchain ──────────────────────────────────────────────
RPC_URL     = _require("RPC_URL")
CHAIN_ID    = int(os.getenv("CHAIN_ID", "11155111"))
PRIVATE_KEY = _require("PRIVATE_KEY")

# ── ERC-8004 Contracts ──────────────────────────────────────
IDENTITY_REGISTRY_ADDRESS   = _require("IDENTITY_REGISTRY_ADDRESS")
REPUTATION_REGISTRY_ADDRESS = _require("REPUTATION_REGISTRY_ADDRESS")
VALIDATION_REGISTRY_ADDRESS = _require("VALIDATION_REGISTRY_ADDRESS")

# ── Additional ERC-8004 Contracts (optional) ───────────────
VALIDATOR_ADDRESS       = os.getenv("VALIDATOR_ADDRESS", "")
RISK_ROUTER_ADDRESS     = os.getenv("RISK_ROUTER_ADDRESS", "")
CAPITAL_VAULT_ADDRESS   = os.getenv("CAPITAL_VAULT_ADDRESS", "")

# ── Trading Parameters ─────────────────────────────────────
MAX_TRADE_USD          = float(os.getenv("MAX_TRADE_USD", "500"))
MAX_DAILY_LOSS_USD     = float(os.getenv("MAX_DAILY_LOSS_USD", "1000"))
TRADING_PAIR           = os.getenv("TRADING_PAIR", "BTC/USDT")
LOOP_INTERVAL_SECONDS  = int(os.getenv("LOOP_INTERVAL_SECONDS", "60"))
TOTAL_CAPITAL_USD      = float(os.getenv("TOTAL_CAPITAL_USD", "10000"))

# ── Agent Identity ──────────────────────────────────────────
AGENT_NAME             = os.getenv("AGENT_NAME", "ProtocolZero")
AGENT_HANDLE           = os.getenv("AGENT_HANDLE", "protocol-zero")
AGENT_VERSION          = os.getenv("AGENT_VERSION", "1.0.0")
