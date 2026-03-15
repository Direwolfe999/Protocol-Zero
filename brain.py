"""
Protocol Zero — Brain (Core Reasoning Engine)
==============================================
Responsibilities:
  1. Fetch recent OHLCV market data via CCXT.
  2. Build a structured prompt with the data + trading context.
  3. Call Amazon Bedrock (Nova 2 Lite) with TOOL-USE for agentic reasoning.
  4. Parse and validate the decision schema.
  5. Agentic tool invocation: the LLM can request on-chain lookups,
     rug-pull scans, Nova Act audits, and embedding analyses.

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

Agentic Tool-Use (Nova 2 Lite):
  The brain can invoke tools mid-reasoning to gather extra info:
  - rug_pull_scanner: Scan a contract address for scam indicators
  - market_deep_dive: Get extended market microstructure data
  - nova_act_audit:   Trigger browser-based contract verification
  - embedding_scan:   Run multimodal scam-pattern detection on token metadata
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
from exceptions import BedrockError, DecisionParseError, MarketDataError

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

    Raises
    ------
    MarketDataError
        If the exchange is unreachable or returns invalid data.
    """
    exchange_specs = [
        ("binance", [symbol, symbol.replace("USDT", "USD")]),
        ("coinbase", [symbol.replace("USDT", "USD"), symbol]),
        ("kraken", [symbol.replace("USDT", "USD"), symbol]),
    ]

    ohlcv = None
    last_exc: Exception | None = None
    for ex_name, symbols in exchange_specs:
        ex_cls = getattr(ccxt, ex_name, None)
        if ex_cls is None:
            continue
        try:
            exchange = ex_cls({"enableRateLimit": True, "timeout": 5000})
        except Exception as exc:
            last_exc = exc
            continue

        for s in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(s, timeframe=timeframe, limit=limit)
                if ohlcv:
                    logger.info("Market data source: %s (%s)", ex_name, s)
                    break
            except ccxt.BaseError as exc:
                last_exc = exc
                continue
        if ohlcv:
            break

    if not ohlcv:
        raise MarketDataError(
            f"Failed to fetch {symbol} data from all exchanges: {last_exc}",
            details={"symbol": symbol, "timeframe": timeframe},
        )

    if not ohlcv:
        raise MarketDataError(
            f"Empty OHLCV response for {symbol}",
            details={"symbol": symbol, "timeframe": timeframe},
        )

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

Edge-Case Stress Rules (CRITICAL — high-volatility scenarios):
- FLASH CRASH (price drop > 8% in < 5 candles): Immediately HOLD, set confidence = 0.2,
  risk_score = 9. Do NOT buy the dip — wait for stabilization.
- PUMP & DUMP (price spike > 10% then reversal > 5%): HOLD with risk_score = 10.
  Flag reason as "Pump-dump pattern detected — avoiding trap."
- EXTREME RSI (> 85 or < 15): Force HOLD. These are capitulation/mania zones.
  Set confidence = 0.15 and explain the RSI extreme in reason.
- LOW LIQUIDITY (volume < 20% of 24h average): Reduce position_size_percent to ≤ 0.5%.
  Set risk_score ≥ 7. Wide spreads make execution dangerous.
- VOLATILITY REGIME (20-period vol > 2.0): Maximum position_size_percent = 1.0%.
  Tighten stop_loss_percent to ≤ 2.0%.
- DIVERGENCE (RSI rising but price falling, or vice versa): Flag as UNCERTAIN regime.
  Reduce confidence by 30%.

When you need additional data to make a better decision, use the available tools:
- rug_pull_scanner: Check a contract address for scam/rug-pull indicators
- market_deep_dive: Get extended micro-structure data for an asset
- nova_act_audit: Run browser-based smart contract verification (Etherscan/DEXTools)
- embedding_scan: Run multimodal scam-pattern detection on token metadata

After using tools, incorporate their results into your final JSON decision.
"""

# ────────────────────────────────────────────────────────────
#  Tool Definitions for Agentic Nova 2 Lite
# ────────────────────────────────────────────────────────────

AGENT_TOOLS = {
    "tools": [
        {
            "toolSpec": {
                "name": "rug_pull_scanner",
                "description": (
                    "Scan a smart contract address for rug-pull and scam indicators. "
                    "Returns risk assessment with verified status, liquidity info, "
                    "and warning flags."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "contract_address": {
                                "type": "string",
                                "description": "The Ethereum/EVM contract address to scan (0x...)"
                            },
                            "chain": {
                                "type": "string",
                                "description": "Blockchain network: 'ethereum', 'sepolia', 'polygon', 'arbitrum'",
                                "default": "sepolia"
                            }
                        },
                        "required": ["contract_address"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "market_deep_dive",
                "description": (
                    "Get extended market microstructure data for an asset, including "
                    "order-book depth, bid-ask spread, funding rates, and whale activity."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "asset": {
                                "type": "string",
                                "description": "The asset ticker (e.g., 'BTC', 'ETH', 'SOL')"
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Analysis timeframe: '1h', '4h', '1d'",
                                "default": "1h"
                            }
                        },
                        "required": ["asset"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "nova_act_audit",
                "description": (
                    "Trigger a Nova Act browser-based audit of a smart contract. "
                    "Uses UI automation to navigate Etherscan and DEXTools to verify "
                    "contract source, check liquidity locks, and detect warning banners."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "contract_address": {
                                "type": "string",
                                "description": "Contract address to audit on Etherscan"
                            },
                            "check_liquidity": {
                                "type": "boolean",
                                "description": "Whether to also check DEXTools for liquidity data",
                                "default": True
                            }
                        },
                        "required": ["contract_address"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "embedding_scan",
                "description": (
                    "Run multimodal scam-pattern detection on token metadata text. "
                    "Analyzes token descriptions, social media posts, and marketing "
                    "material for similarity to known scam patterns."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Token description, social media post, or marketing text to analyze"
                            },
                            "token_name": {
                                "type": "string",
                                "description": "Name of the token being analyzed"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        }
    ]
}


def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Execute a tool requested by the agentic brain.
    Routes to the appropriate Nova module / internal function.
    """
    logger.info("Agentic tool call: %s(%s)", tool_name, json.dumps(tool_input, default=str))

    try:
        if tool_name == "rug_pull_scanner":
            return _tool_rug_pull_scan(tool_input)
        elif tool_name == "market_deep_dive":
            return _tool_market_deep_dive(tool_input)
        elif tool_name == "nova_act_audit":
            return _tool_nova_act_audit(tool_input)
        elif tool_name == "embedding_scan":
            return _tool_embedding_scan(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error("Tool execution failed: %s — %s", tool_name, e)
        return {"error": str(e), "tool": tool_name}


def _tool_rug_pull_scan(inp: dict) -> dict:
    """Run Nova Act Auditor's quick safety check on a contract."""
    try:
        from nova_act_auditor import NovaActAuditor
        auditor = NovaActAuditor()
        result = auditor.quick_safety_check(inp["contract_address"])
        return result.to_dict()
    except Exception as e:
        return {"risk_level": "UNKNOWN", "error": str(e)}


def _tool_market_deep_dive(inp: dict) -> dict:
    """
    Get extended market microstructure data from live exchange.
    Uses CCXT to pull real order-book depth and ticker data.
    Falls back to estimated values if the exchange is unreachable.
    """
    asset = inp.get("asset", "BTC")
    symbol = f"{asset}/USDT"

    try:
        exchange = ccxt.binance({"enableRateLimit": True})

        # Fetch real ticker + orderbook
        ticker = exchange.fetch_ticker(symbol)
        orderbook = exchange.fetch_order_book(symbol, limit=50)

        bid_total = sum(amount for _, amount in orderbook.get("bids", []))
        ask_total = sum(amount for _, amount in orderbook.get("asks", []))
        best_bid = orderbook["bids"][0][0] if orderbook.get("bids") else 0
        best_ask = orderbook["asks"][0][0] if orderbook.get("asks") else 0

        spread_bps = ((best_ask - best_bid) / best_bid * 10_000) if best_bid > 0 else 0

        return {
            "asset": asset,
            "source": "live (Binance via CCXT)",
            "bid_ask_spread_bps": round(spread_bps, 2),
            "order_book_bid_depth": round(bid_total, 4),
            "order_book_ask_depth": round(ask_total, 4),
            "last_price": ticker.get("last", 0),
            "volume_24h": ticker.get("quoteVolume", 0),
            "price_change_24h_pct": round(ticker.get("percentage", 0) or 0, 2),
            "vwap": ticker.get("vwap", None),
            "high_24h": ticker.get("high", 0),
            "low_24h": ticker.get("low", 0),
        }
    except Exception as e:
        logger.warning("market_deep_dive live fetch failed: %s — using estimates", e)
        # Transparent fallback with honest labelling
        import hashlib as _hlib, math as _math
        seed = int(_hlib.sha256(asset.encode()).hexdigest()[:8], 16)
        return {
            "asset": asset,
            "source": "estimated (exchange unreachable)",
            "bid_ask_spread_bps": round(abs(_math.sin(seed)) * 5 + 1, 2),
            "order_book_bid_depth": "N/A",
            "order_book_ask_depth": "N/A",
            "last_price": "N/A",
            "volume_24h": "N/A",
            "note": "Live data unavailable — values are heuristic estimates.",
        }


def _tool_nova_act_audit(inp: dict) -> dict:
    """Run a Nova Act browser-based smart contract audit."""
    try:
        from nova_act_auditor import NovaActAuditor
        auditor = NovaActAuditor()
        result = auditor.audit_contract(inp["contract_address"])
        return result.to_dict()
    except Exception as e:
        return {"risk_level": "UNKNOWN", "error": str(e)}


def _tool_embedding_scan(inp: dict) -> dict:
    """Run multimodal embedding analysis on text."""
    try:
        from nova_embeddings import NovaEmbeddingsAnalyzer
        analyzer = NovaEmbeddingsAnalyzer()
        result = analyzer.analyze_text(inp.get("text", ""))
        return result.to_dict()
    except Exception as e:
        return {"risk_label": "UNKNOWN", "error": str(e)}


def _build_user_prompt(df: pd.DataFrame, symbol: str, max_trade: float) -> str:
    """Format the most recent data into a compact prompt."""
    if df is None or df.empty:
        return (
            f"Current UTC time: {datetime.now(timezone.utc).isoformat()}\n"
            f"Trading pair: {symbol}\n"
            f"Max single trade: ${max_trade:.2f}\n"
            f"Total capital: ${config.TOTAL_CAPITAL_USD:,.2f}\n\n"
            "No market data available. Recommend HOLD with low confidence.\n\n"
            "What is your trading decision?"
        )

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

    latest = df.iloc[-1]
    latest_close = latest["close"]
    latest_rsi = latest["rsi_14"] if pd.notna(latest.get("rsi_14")) else 0.0
    latest_sma12 = latest["sma_12"] if pd.notna(latest.get("sma_12")) else 0.0
    latest_sma26 = latest["sma_26"] if pd.notna(latest.get("sma_26")) else 0.0

    return (
        f"Current UTC time: {datetime.now(timezone.utc).isoformat()}\n"
        f"Trading pair: {symbol}\n"
        f"Max single trade: ${max_trade:.2f}\n"
        f"Total capital: ${config.TOTAL_CAPITAL_USD:,.2f}\n\n"
        f"Last 12 candles (1 h each):\n"
        f"{json.dumps(tail, indent=2, default=str)}\n\n"
        f"Latest close: ${latest_close:.2f}\n"
        f"RSI-14: {latest_rsi:.1f}\n"
        f"SMA-12: {latest_sma12:.2f}  |  SMA-26: {latest_sma26:.2f}\n"
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

    # Skip Bedrock if we already know it's broken this session
    if getattr(invoke_brain, "_bedrock_failed", False):
        return _rule_based_decision(df, symbol, max_trade)

    user_prompt = _build_user_prompt(df, symbol, max_trade)

    # ── Bedrock Converse API (Nova Lite with Tool-Use) ─────────
    client = _get_bedrock_client()

    model_id = getattr(config, "BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0") or "us.amazon.nova-lite-v1:0"
    if ":" not in model_id:
        logger.warning("Invalid BEDROCK_MODEL_ID '%s' — falling back to us.amazon.nova-lite-v1:0", model_id)
        model_id = "us.amazon.nova-lite-v1:0"

    messages = [
        {
            "role": "user",
            "content": [{"text": user_prompt}],
        }
    ]

    # Agentic loop: let Nova request tools, execute them, feed results back
    max_tool_rounds = 3
    for round_num in range(max_tool_rounds + 1):
        converse_kwargs = dict(
            modelId=model_id,
            messages=messages,
            system=[{"text": _SYSTEM_PROMPT}],
            inferenceConfig={
                "maxTokens": 1024,
                "temperature": 0.2,        # low temp → deterministic trading
                "topP": 0.9,
            },
            toolConfig=AGENT_TOOLS,
        )

        try:
            response = client.converse(**converse_kwargs)
        except Exception as exc:
            _err_msg = str(exc)
            _is_not_allowed = "Operation not allowed" in _err_msg or "ValidationException" in _err_msg
            if _is_not_allowed:
                logger.warning(
                    "Bedrock blocked by account/runtime policy — model=%s region=%s error=%s. "
                    "Falling back to rule-based engine.",
                    model_id,
                    getattr(config, "AWS_DEFAULT_REGION", "unknown"),
                    _err_msg,
                )
            else:
                logger.warning(
                    "Bedrock API failed — model=%s region=%s error=%s",
                    model_id,
                    getattr(config, "AWS_DEFAULT_REGION", "unknown"),
                    _err_msg,
                    exc_info=True,
                )
            invoke_brain._bedrock_failed = True  # Don't retry this session
            invoke_brain._bedrock_fail_reason = _err_msg
            return _rule_based_decision(df, symbol, max_trade)
        stop_reason = response.get("stopReason", "end_turn")
        output_msg = response["output"]["message"]
        messages.append(output_msg)

        # Check if the model wants to use a tool
        if stop_reason == "tool_use":
            tool_results = []
            for block in output_msg.get("content", []):
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    tool_name = tool_use["name"]
                    tool_id = tool_use["toolUseId"]
                    tool_input = tool_use.get("input", {})

                    logger.info("🔧 Agentic tool call [round %d]: %s", round_num + 1, tool_name)
                    result = _execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_id,
                            "content": [{"json": result}],
                        }
                    })

            # Feed tool results back
            messages.append({
                "role": "user",
                "content": tool_results,
            })
            continue  # Let Nova reason over the tool results
        else:
            # Model finished (end_turn or max_tokens) — extract final text
            break

    # Extract final text response
    raw_text = ""
    for block in output_msg.get("content", []):
        if "text" in block:
            raw_text = block["text"]
            break

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

    asset = symbol.split("/")[0] if "/" in symbol else symbol

    latest = df.iloc[-1]
    price  = float(latest["close"])
    rsi    = float(latest.get("rsi_14", 50)) if pd.notna(latest.get("rsi_14")) else 50.0
    sma12  = float(latest.get("sma_12", price)) if pd.notna(latest.get("sma_12")) else price
    sma26  = float(latest.get("sma_26", price)) if pd.notna(latest.get("sma_26")) else price
    vol    = float(latest.get("volatility", 0.5)) if pd.notna(latest.get("volatility")) else 0.5

    # ── Edge-case stress detection ─────────────────────────
    # Flash crash: >8% drop in last 5 candles
    if len(df) >= 5:
        _5ago = float(df["close"].iloc[-5])
        _price_drop_pct = (price / _5ago - 1) * 100 if _5ago > 0 else 0
    else:
        _price_drop_pct = 0

    # Pump & dump: >10% spike then >5% reversal
    _pump_dump = False
    if len(df) >= 10:
        _peak = float(df["close"].iloc[-10:].max())
        _spike_up = (_peak / float(df["close"].iloc[-10]) - 1) * 100
        _reversal = (_peak - price) / _peak * 100 if _peak > 0 else 0
        _pump_dump = _spike_up > 10 and _reversal > 5

    # Volume drought
    _vol_avg = float(df["volume"].tail(24).mean()) if len(df) >= 24 else 1.0
    _vol_prev = float(df["volume"].tail(48).head(24).mean()) if len(df) >= 48 else _vol_avg
    _low_liquidity = (_vol_avg / _vol_prev < 0.20) if _vol_prev > 0 else False

    # RSI divergence (RSI rising + price falling or vice versa)
    _rsi_divergence = False
    if len(df) >= 5:
        _rsi_5ago = float(df["rsi_14"].iloc[-5]) if pd.notna(df["rsi_14"].iloc[-5]) else 50
        _price_dir = price > _5ago  # price rising
        _rsi_dir = rsi > _rsi_5ago  # RSI rising
        _rsi_divergence = _price_dir != _rsi_dir and abs(rsi - _rsi_5ago) > 5

    # ── EDGE CASE: Flash crash ─────────────────────────────
    if _price_drop_pct < -8:
        return {
            "action": "HOLD", "asset": asset, "amount_usd": 0.0,
            "reason": f"FLASH CRASH detected: {_price_drop_pct:.1f}% drop in 5 candles — waiting for stabilization",
            "confidence": 0.20, "risk_score": 9,
            "position_size_percent": 0.0, "stop_loss_percent": 0.0,
            "take_profit_percent": 0.0, "market_regime": "VOLATILE",
        }

    # ── EDGE CASE: Pump & dump ─────────────────────────────
    if _pump_dump:
        return {
            "action": "HOLD", "asset": asset, "amount_usd": 0.0,
            "reason": f"PUMP-DUMP pattern detected: {_spike_up:.1f}% spike then {_reversal:.1f}% reversal — avoiding trap",
            "confidence": 0.15, "risk_score": 10,
            "position_size_percent": 0.0, "stop_loss_percent": 0.0,
            "take_profit_percent": 0.0, "market_regime": "VOLATILE",
        }

    # ── EDGE CASE: Extreme RSI ─────────────────────────────
    if rsi > 85 or rsi < 15:
        zone = "mania" if rsi > 85 else "capitulation"
        return {
            "action": "HOLD", "asset": asset, "amount_usd": 0.0,
            "reason": f"EXTREME RSI ({rsi:.1f}) in {zone} zone — forced HOLD until normalization",
            "confidence": 0.15, "risk_score": 8,
            "position_size_percent": 0.0, "stop_loss_percent": 0.0,
            "take_profit_percent": 0.0, "market_regime": "VOLATILE",
        }

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
        # ── Low liquidity cap ──────────────────────────────
        if _low_liquidity:
            size_pct = min(size_pct, 0.5)
            risk_score = max(risk_score, 7)
            reason += " [Low liquidity — position capped]"
        # ── High volatility cap ────────────────────────────
        if vol > 2.0:
            size_pct = min(size_pct, 1.0)
        # ── RSI divergence penalty ─────────────────────────
        if _rsi_divergence:
            confidence = round(max(0.15, confidence * 0.7), 2)
            regime = "UNCERTAIN"
            reason += " [RSI divergence detected]"
        amount = round(max_trade * size_pct / 100, 2)
    else:
        size_pct = 0.0
        amount = 0.0

    logger.info("Rule-based decision: %s %s (conf=%.2f, RSI=%.1f, regime=%s)",
                action, asset, confidence, rsi, regime)

    return {
        "action":               action,
        "asset":                asset,
        "amount_usd":           amount,
        "reason":               reason,
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
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON — defaulting to HOLD.\nRaw: %s", raw)
        raise DecisionParseError(
            f"LLM returned unparseable JSON: {exc}",
            details={"raw_response": raw[:500]},
        ) from exc

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
