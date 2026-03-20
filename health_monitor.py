"""Runtime health probe helpers for Protocol Zero dashboard."""

from __future__ import annotations

import os
import time
from typing import Any, Callable


def bedrock_runtime_probe(
    cloud_safe_mode: bool,
    config_module: Any,
    aws_access_key: str,
    aws_secret_key: str,
    bedrock_api_key: str = "",
) -> tuple[str, int, str]:
    """Return (status, latency_ms, detail) based on a Bedrock runtime call."""
    if cloud_safe_mode:
        return "READY", 0, "Cloud-safe mode"

    _ak = (aws_access_key or bedrock_api_key or "").strip()
    _sk = (aws_secret_key or "").strip()
    if not _ak or _ak in ("your_aws_access_key", "your-access-key-id"):
        return "FALLBACK", 0, "No credentials"

    _t = time.perf_counter()
    try:
        import boto3 as _boto3_hc

        _region = getattr(config_module, "AWS_DEFAULT_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        _model = getattr(config_module, "BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
        _kwargs: dict[str, Any] = {"region_name": _region, "aws_access_key_id": _ak}
        if _sk:
            _kwargs["aws_secret_access_key"] = _sk
        _client = _boto3_hc.client("bedrock-runtime", **_kwargs)
        _client.converse(
            modelId=_model,
            messages=[{"role": "user", "content": [{"text": "health-check"}]}],
            inferenceConfig={"maxTokens": 1, "temperature": 0.0},
        )
        return "READY", round((time.perf_counter() - _t) * 1000), "Runtime invoke OK"
    except Exception as exc:
        _msg = str(exc)
        _ms = round((time.perf_counter() - _t) * 1000)
        if "Operation not allowed" in _msg or "ValidationException" in _msg:
            return "BLOCKED", _ms, "Runtime blocked"
        return "FALLBACK", _ms, "Runtime unavailable"


def system_health_check(
    cloud_safe_mode: bool,
    rpc_url: str,
    bedrock_probe: Callable[[], tuple[str, int, str]],
) -> dict[str, tuple[str, str, int]]:
    """Ping subsystem health and return name -> (icon, status, latency_ms)."""
    checks: dict[str, tuple[str, str, int]] = {}

    if cloud_safe_mode:
        checks["Market Feed"] = ("📡", "LIVE", 0)
        checks["Sepolia RPC"] = ("⛓️", "LIVE", 0)
        checks["AWS Bedrock"] = ("🧠", "READY", 0)
        return checks

    _t = time.perf_counter()
    try:
        import ccxt as _ccxt_hc

        _feed_name = "Binance Feed"
        _feed_status = "OFF"
        _feed_ms = 0

        try:
            _ccxt_hc.binance({"enableRateLimit": False, "timeout": 3000}).fetch_ticker("ETH/USDT")
            _feed_status = "LIVE"
            _feed_ms = round((time.perf_counter() - _t) * 1000)
        except Exception:
            for _ex_name in ("coinbase", "kraken", "bitfinex"):
                try:
                    _ex_cls = getattr(_ccxt_hc, _ex_name, None)
                    if _ex_cls is None:
                        continue
                    _ex_cls({"enableRateLimit": False, "timeout": 3000}).fetch_ticker("ETH/USD")
                    _feed_name = f"{_ex_name.capitalize()} Feed"
                    _feed_status = "FALLBACK"
                    _feed_ms = round((time.perf_counter() - _t) * 1000)
                    break
                except Exception:
                    continue

        checks[_feed_name] = ("📡", _feed_status, _feed_ms)
    except Exception:
        checks["Binance Feed"] = ("📡", "OFF", 0)

    _t = time.perf_counter()
    try:
        from web3 import Web3 as _W3hc

        _w3 = _W3hc(_W3hc.HTTPProvider(rpc_url or "", request_kwargs={"timeout": 4}))
        _w3.eth.block_number
        checks["Sepolia RPC"] = ("⛓️", "LIVE", round((time.perf_counter() - _t) * 1000))
    except Exception:
        checks["Sepolia RPC"] = ("⛓️", "OFF", 0)

    _b_status, _b_ms, _ = bedrock_probe()
    checks["AWS Bedrock"] = ("🧠", _b_status, _b_ms)
    return checks
