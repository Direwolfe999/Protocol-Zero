"""
Protocol Zero — Brain (Core Reasoning Engine)
==============================================
Responsibilities:
  1. Fetch recent OHLCV market data via CCXT.
  2. Build a structured prompt with the data + trading context.
  3. Call Amazon Bedrock (Nova Lite) to get a JSON decision.
  4. Parse and validate the decision schema.

Decision schema returned by the LLM (ERC-8004 compliant):
{
    "action":               "BUY" | "SELL" | "HOLD",
    "asset":                "BTC",
    "amount_usd":           <float>,
    "reason":               "short human-readable rationale",
    "confidence":           0.0 – 1.0,
    "risk_score":           1 – 10,
    "position_size_percent": 0.0 – 2.0,
    "stop_loss_percent":    <float>,
    "take_profit_percent":  <float>,
    "market_regime":        "TRENDING" | "RANGING" | "VOLATILE" | "UNCERTAIN"
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
import ccxt
import pandas as pd

import config

logger = logging.getLogger("protocol_zero.brain")

# ────────────────────────────────────────────────────────────
#  Market Data Fetcher
# ────────────────────────────────────────────────────────────

def fetch_market_data(
    symbol: str = config.TRADING_PAIR,
    timeframe: str = "1h",
    limit: int = 48,
) -> pd.DataFrame:
    """
    Pull the last *limit* candles from a public exchange via CCXT.
    Returns a DataFrame with columns:
        timestamp, open, high, low, close, volume
    """
    exchange = ccxt.binance({"enableRateLimit": True})   # no auth needed for public data
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    # ── Derive simple technical indicators ──────────────────
    df["sma_12"] = df["close"].rolling(window=12).mean()
    df["sma_26"] = df["close"].rolling(window=26).mean()
    df["rsi_14"] = _compute_rsi(df["close"], 14)
    df["pct_change"] = df["close"].pct_change() * 100  # % move per candle

    logger.info("Fetched %d candles for %s (%s)", len(df), symbol, timeframe)
    return df


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index — classic Wilder smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ────────────────────────────────────────────────────────────
#  Prompt Builder
# ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Protocol Zero — an autonomous ERC-8004 compliant DeFi trading agent.
Your mandate is capital preservation first, profit second.

You MUST reply with a single JSON object. No markdown, no explanation outside the JSON.

Schema:
{
  "action":               "BUY" | "SELL" | "HOLD",
  "asset":                "<TICKER>",
  "amount_usd":           <float — dollar amount for this trade>,
  "reason":               "<one sentence rationale>",
  "confidence":           <float 0.0-1.0>,
  "risk_score":           <integer 1-10, where 1=safest 10=riskiest>,
  "position_size_percent": <float 0.0-2.0 — percent of capital>,
  "stop_loss_percent":    <float — e.g. 3.0 for 3% stop loss>,
  "take_profit_percent":  <float — e.g. 6.0 for 6% take profit>,
  "market_regime":        "TRENDING" | "RANGING" | "VOLATILE" | "UNCERTAIN"
}

Rules:
- Never exceed the max trade size provided.
- If uncertain, choose HOLD with confidence < 0.6.
- Every BUY/SELL MUST have stop_loss_percent and take_profit_percent set > 0.
- risk_score: 1-3 = low risk, 4-6 = moderate, 7-10 = high risk.
- position_size_percent must never exceed 2.0.
- Base decisions on price momentum, RSI, SMA crossovers, volume, and volatility.
- Assess market_regime from the data: TRENDING (clear direction), RANGING (sideways),
  VOLATILE (high variance), UNCERTAIN (mixed signals).
"""


def _build_user_prompt(df: pd.DataFrame, symbol: str, max_trade: float) -> str:
    """Format the most recent data into a compact prompt."""
    tail = df.tail(12).to_dict(orient="records")
    # Serialize timestamps
    for row in tail:
        if isinstance(row.get("timestamp"), pd.Timestamp):
            row["timestamp"] = row["timestamp"].isoformat()

    # Compute volatility metrics for regime detection
    volatility = df["close"].pct_change().rolling(20).std().iloc[-1]
    vol_str = f"{volatility:.4f}" if pd.notna(volatility) else "N/A"

    # Volume analysis
    vol_24h = df["volume"].tail(24).mean()
    vol_prev = df["volume"].tail(48).head(24).mean()
    vol_change = ((vol_24h / vol_prev - 1) * 100) if vol_prev > 0 else 0

    return (
        f"Current UTC time: {datetime.now(timezone.utc).isoformat()}\n"
        f"Trading pair: {symbol}\n"
        f"Max single trade: ${max_trade:.2f}\n"
        f"Total capital: ${config.TOTAL_CAPITAL_USD:,.2f}\n\n"
        f"Last 12 candles (1 h each):\n"
        f"{json.dumps(tail, indent=2, default=str)}\n\n"
        f"Latest close: ${df['close'].iloc[-1]:.2f}\n"
        f"RSI-14: {df['rsi_14'].iloc[-1]:.1f}\n"
        f"SMA-12: {df['sma_12'].iloc[-1]:.2f}  |  SMA-26: {df['sma_26'].iloc[-1]:.2f}\n"
        f"20-period volatility: {vol_str}\n"
        f"Volume trend: {vol_change:+.1f}% vs prior 24h\n\n"
        "What is your trading decision?"
    )


# ────────────────────────────────────────────────────────────
#  Bedrock Inference
# ────────────────────────────────────────────────────────────

def _get_bedrock_client() -> Any:
    """Construct a boto3 Bedrock Runtime client."""
    return boto3.client(
        "bedrock-runtime",
        region_name=config.AWS_DEFAULT_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    )


def invoke_brain(
    df: pd.DataFrame | None = None,
    symbol: str = config.TRADING_PAIR,
    max_trade: float = config.MAX_TRADE_USD,
) -> dict:
    """
    End-to-end reasoning step:
      1. Fetch market data (or use supplied df).
      2. Build prompt.
      3. Call Nova Lite on Bedrock.
      4. Parse the JSON decision.

    Falls back to a rule-based engine when AWS credentials
    are not yet configured (config.AWS_READY == False).

    Returns
    -------
    dict  — validated decision with keys: action, asset, amount_usd, reason, confidence
    """
    if df is None:
        df = fetch_market_data(symbol)

    # ── Fallback: rule-based engine when AWS is unavailable ─
    if not getattr(config, "AWS_READY", False):
        logger.info("AWS credentials not ready — using rule-based fallback brain")
        return _rule_based_decision(df, symbol, max_trade)

    user_prompt = _build_user_prompt(df, symbol, max_trade)

    # ── Bedrock Converse API (Nova Lite) ────────────────────
    client = _get_bedrock_client()

    response = client.converse(
        modelId=config.BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": f"{_SYSTEM_PROMPT}\n\n{user_prompt}"}],
            }
        ],
        inferenceConfig={
            "maxTokens": 512,
            "temperature": 0.2,        # low temp → deterministic trading
            "topP": 0.9,
        },
    )

    raw_text: str = response["output"]["message"]["content"][0]["text"]
    logger.debug("Raw Bedrock response:\n%s", raw_text)

    decision = _parse_decision(raw_text)
    return decision


# ────────────────────────────────────────────────────────────
#  Rule-Based Fallback (used when AWS creds are missing)
# ────────────────────────────────────────────────────────────

def _rule_based_decision(
    df: pd.DataFrame, symbol: str, max_trade: float
) -> dict:
    """
    Technical-indicator-driven decision engine.
    Uses RSI, SMA crossover, and volatility to produce a trade decision
    identical in schema to the Nova LLM output.
    """
    if df is None or len(df) < 26:
        return _default_hold()

    latest = df.iloc[-1]
    price  = float(latest["close"])
    rsi    = float(latest.get("rsi_14", 50)) if pd.notna(latest.get("rsi_14")) else 50.0
    sma12  = float(latest.get("sma_12", price)) if pd.notna(latest.get("sma_12")) else price
    sma26  = float(latest.get("sma_26", price)) if pd.notna(latest.get("sma_26")) else price
    vol    = float(latest.get("volatility", 0.5)) if pd.notna(latest.get("volatility")) else 0.5

    # Regime detection
    if vol > 2.0:
        regime = "VOLATILE"
    elif abs(sma12 - sma26) / price > 0.01:
        regime = "TRENDING"
    elif vol < 0.5:
        regime = "RANGING"
    else:
        regime = "UNCERTAIN"

    # Decision logic
    action = "HOLD"
    reason = ""
    confidence = 0.0
    risk_score = 5

    if rsi < 30 and sma12 > sma26:
        action = "BUY"
        confidence = min(0.85, (30 - rsi) / 30 + 0.4)
        risk_score = 3
        reason = f"RSI oversold ({rsi:.1f}) + bullish SMA crossover — buying opportunity"
    elif rsi < 35 and regime != "VOLATILE":
        action = "BUY"
        confidence = 0.55
        risk_score = 4
        reason = f"RSI approaching oversold ({rsi:.1f}) in {regime} regime"
    elif rsi > 70 and sma12 < sma26:
        action = "SELL"
        confidence = min(0.85, (rsi - 70) / 30 + 0.4)
        risk_score = 3
        reason = f"RSI overbought ({rsi:.1f}) + bearish SMA crossover — take profit"
    elif rsi > 65 and regime == "VOLATILE":
        action = "SELL"
        confidence = 0.60
        risk_score = 5
        reason = f"RSI elevated ({rsi:.1f}) in volatile regime — risk reduction"
    elif regime == "VOLATILE":
        action = "HOLD"
        confidence = 0.7
        risk_score = 7
        reason = f"High volatility ({vol:.2f}) — waiting for stability"
    else:
        action = "HOLD"
        confidence = 0.5
        risk_score = 5
        reason = f"No clear signal — RSI {rsi:.1f}, regime {regime}"

    # Position sizing
    if action in ("BUY", "SELL"):
        size_pct = min(2.0, confidence * 1.5)
        amount = round(max_trade * size_pct / 100, 2)
    else:
        size_pct = 0.0
        amount = 0.0

    asset = symbol.split("/")[0] if "/" in symbol else symbol

    logger.info("Rule-based decision: %s %s (conf=%.2f, RSI=%.1f, regime=%s)",
                action, asset, confidence, rsi, regime)

    return {
        "action":               action,
        "asset":                asset,
        "amount_usd":           amount,
        "reason":               f"[Rule Engine] {reason}",
        "confidence":           round(confidence, 2),
        "risk_score":           risk_score,
        "position_size_percent": round(size_pct, 2),
        "stop_loss_percent":    3.0,
        "take_profit_percent":  6.0,
        "market_regime":        regime,
    }


# ────────────────────────────────────────────────────────────
#  Response Parser & Validator
# ────────────────────────────────────────────────────────────

_VALID_ACTIONS = {"BUY", "SELL", "HOLD"}


def _parse_decision(raw: str) -> dict:
    """
    Extract the JSON decision from the LLM response.
    Falls back to HOLD if parsing fails — never crash.
    """
    # Strip markdown code fences if the LLM wraps its answer
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON — defaulting to HOLD.\nRaw: %s", raw)
        return _default_hold()

    # Validate required keys
    action = str(data.get("action", "HOLD")).upper()
    if action not in _VALID_ACTIONS:
        action = "HOLD"

    # Parse market regime
    regime = str(data.get("market_regime", "UNCERTAIN")).upper()
    if regime not in {"TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"}:
        regime = "UNCERTAIN"

    return {
        "action":               action,
        "asset":                str(data.get("asset", "BTC")),
        "amount_usd":           float(data.get("amount_usd", 0)),
        "reason":               str(data.get("reason", "No reason provided")),
        "confidence":           min(max(float(data.get("confidence", 0)), 0.0), 1.0),
        "risk_score":           min(10, max(1, int(data.get("risk_score", 5)))),
        "position_size_percent": min(2.0, max(0.0, float(data.get("position_size_percent", 0)))),
        "stop_loss_percent":    max(0.0, float(data.get("stop_loss_percent", 3.0))),
        "take_profit_percent":  max(0.0, float(data.get("take_profit_percent", 6.0))),
        "market_regime":        regime,
    }


def _default_hold() -> dict:
    return {
        "action":               "HOLD",
        "asset":                "BTC",
        "amount_usd":           0.0,
        "reason":               "LLM parse failure — safety default",
        "confidence":           0.0,
        "risk_score":           5,
        "position_size_percent": 0.0,
        "stop_loss_percent":    0.0,
        "take_profit_percent":  0.0,
        "market_regime":        "UNCERTAIN",
    }
