"""
Protocol Zero — Exceptions Hierarchy Unit Tests
=================================================
Tests the custom exception hierarchy for correct inheritance
and detail propagation.
"""

from __future__ import annotations

import pytest

from exceptions import (
    ProtocolZeroError,
    ConfigurationError,
    MarketDataError,
    BrainError,
    BedrockError,
    DecisionParseError,
    RiskCheckError,
    SigningError,
    ChainError,
    TransactionError,
    RegistryError,
    DexExecutionError,
)


class TestExceptionHierarchy:
    """All custom exceptions inherit from ProtocolZeroError."""

    def test_base_exception(self) -> None:
        err = ProtocolZeroError("test error", details={"key": "value"})
        assert str(err) == "test error"
        assert err.details == {"key": "value"}

    def test_configuration_error(self) -> None:
        err = ConfigurationError("missing key")
        assert isinstance(err, ProtocolZeroError)

    def test_market_data_error(self) -> None:
        err = MarketDataError("exchange down", details={"symbol": "BTC/USDT"})
        assert isinstance(err, ProtocolZeroError)
        assert err.details["symbol"] == "BTC/USDT"

    def test_brain_error_hierarchy(self) -> None:
        assert issubclass(BedrockError, BrainError)
        assert issubclass(DecisionParseError, BrainError)
        assert issubclass(BrainError, ProtocolZeroError)

    def test_chain_error_hierarchy(self) -> None:
        assert issubclass(TransactionError, ChainError)
        assert issubclass(RegistryError, ChainError)
        assert issubclass(ChainError, ProtocolZeroError)

    def test_signing_error(self) -> None:
        err = SigningError("bad key")
        assert isinstance(err, ProtocolZeroError)

    def test_dex_execution_error(self) -> None:
        err = DexExecutionError("slippage too high")
        assert isinstance(err, ProtocolZeroError)

    def test_risk_check_error(self) -> None:
        err = RiskCheckError("internal failure")
        assert isinstance(err, ProtocolZeroError)

    def test_details_default_empty(self) -> None:
        err = ProtocolZeroError("no details")
        assert err.details == {}

    def test_bedrock_error_with_details(self) -> None:
        err = BedrockError("model not found", details={"model": "nova-lite"})
        assert isinstance(err, BrainError)
        assert isinstance(err, ProtocolZeroError)
        assert err.details["model"] == "nova-lite"

    def test_catchable_by_base(self) -> None:
        """All exceptions should be catchable by ProtocolZeroError."""
        with pytest.raises(ProtocolZeroError):
            raise TransactionError("test")

        with pytest.raises(ProtocolZeroError):
            raise DecisionParseError("test")

        with pytest.raises(ProtocolZeroError):
            raise DexExecutionError("test")
