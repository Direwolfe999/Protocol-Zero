"""
Protocol Zero — Custom Exception Hierarchy
============================================
Structured exceptions for clear error handling across the pipeline.

Hierarchy:
    ProtocolZeroError
    ├── ConfigurationError      — missing or invalid .env / config values
    ├── MarketDataError         — CCXT / exchange data fetch failures
    ├── BrainError              — AI reasoning failures (Bedrock, parsing)
    │   ├── BedrockError        — AWS Bedrock API errors
    │   └── DecisionParseError  — invalid JSON from the LLM
    ├── RiskCheckError          — risk gate internal errors
    ├── SigningError            — EIP-712 signing failures
    ├── ChainError              — on-chain interaction failures
    │   ├── TransactionError    — TX build / send / revert errors
    │   └── RegistryError       — ERC-8004 registry call errors
    └── DexExecutionError       — Uniswap / DEX swap failures
"""

from __future__ import annotations


class ProtocolZeroError(Exception):
    """Base exception for all Protocol Zero errors."""

    def __init__(self, message: str = "", details: dict | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


# ── Configuration ──────────────────────────────────────────

class ConfigurationError(ProtocolZeroError):
    """Raised when environment variables or config values are missing / invalid."""


# ── Market Data ────────────────────────────────────────────

class MarketDataError(ProtocolZeroError):
    """Raised when market data cannot be fetched or is malformed."""


# ── Brain / AI ─────────────────────────────────────────────

class BrainError(ProtocolZeroError):
    """Raised when the AI reasoning engine fails."""


class BedrockError(BrainError):
    """Raised when Amazon Bedrock returns an error."""


class DecisionParseError(BrainError):
    """Raised when the LLM response cannot be parsed into a valid decision."""


# ── Risk ───────────────────────────────────────────────────

class RiskCheckError(ProtocolZeroError):
    """Raised when the risk gate encounters an internal error."""


# ── Signing ────────────────────────────────────────────────

class SigningError(ProtocolZeroError):
    """Raised when EIP-712 signing fails."""


# ── Chain Interaction ──────────────────────────────────────

class ChainError(ProtocolZeroError):
    """Raised when on-chain interaction fails."""


class TransactionError(ChainError):
    """Raised when a transaction cannot be built, sent, or is reverted."""


class RegistryError(ChainError):
    """Raised when an ERC-8004 registry call fails."""


# ── DEX Execution ──────────────────────────────────────────

class DexExecutionError(ProtocolZeroError):
    """Raised when a DEX swap cannot be executed."""
