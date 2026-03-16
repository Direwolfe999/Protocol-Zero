"""Streamlit Cloud entrypoint for Protocol Zero.

This entrypoint bootstraps safe defaults so Streamlit Community Cloud can
always start the dashboard, even when full blockchain/AWS secrets are absent.
Real secrets (if configured) still take precedence.
"""

from __future__ import annotations

import os


def _set_default_env(key: str, value: str) -> None:
	"""Set env var only when not already provided by the host/secrets."""
	if not os.getenv(key):
		os.environ[key] = value


# ── Cloud-safe defaults (non-destructive; real secrets override these) ──
_set_default_env("PZ_CLOUD_SAFE_MODE", "1")
_set_default_env("PZ_FORCE_DASHBOARD_MODE", "1")

# Required config vars (for graceful dashboard boot on Streamlit Cloud)
_set_default_env("RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
_set_default_env(
	"PRIVATE_KEY",
	"1111111111111111111111111111111111111111111111111111111111111111",
)
_set_default_env("IDENTITY_REGISTRY_ADDRESS", "0x000000000000000000000000000000000000dEaD")
_set_default_env("REPUTATION_REGISTRY_ADDRESS", "0x000000000000000000000000000000000000bEEF")
_set_default_env("VALIDATION_REGISTRY_ADDRESS", "0x000000000000000000000000000000000000c0Fe")
_set_default_env("CHAIN_ID", "11155111")
_set_default_env("DEX_ENABLED", "false")

import dashboard  # noqa: E402,F401
