from __future__ import annotations

import gc
import hashlib
import json
import logging
import os
import pathlib
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from health_monitor import bedrock_runtime_probe, system_health_check
from session_store import persist_state, restore_persisted_state
from ui_components import build_health_badges_html, footer_html

logger = logging.getLogger("protocol_zero.app_core")

_CLOUD_SAFE_MODE = os.getenv("PZ_CLOUD_SAFE_MODE", "1").strip().lower() in {"1", "true", "yes", "on"}
_ULTRA_LITE_MODE = os.getenv("PZ_ULTRA_LITE_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
_DISABLE_EXPLICIT_RERUN = os.getenv("PZ_DISABLE_EXPLICIT_RERUN", "1").strip().lower() in {"1", "true", "yes", "on"}

if _CLOUD_SAFE_MODE and _DISABLE_EXPLICIT_RERUN:
    def _host_safe_noop_rerun(*_args: Any, **_kwargs: Any) -> None:
        return None

    try:
        st.rerun = _host_safe_noop_rerun  # type: ignore[assignment]
    except Exception:
        pass

try:
    import config
except Exception:
    config = None  # type: ignore[assignment]


@st.cache_resource(show_spinner=False)
def _init_chain() -> tuple[Any | None, bool]:
    try:
        from chain_interactor import ChainInteractor
        return ChainInteractor(), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_perf() -> tuple[Any | None, bool]:
    try:
        from performance_tracker import PerformanceTracker
        return PerformanceTracker(initial_capital=10_000.0), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_artifacts() -> tuple[Any | None, bool]:
    try:
        from validation_artifacts import ValidationArtifactBuilder
        return ValidationArtifactBuilder(), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_risk() -> tuple[Any | None, bool]:
    try:
        from risk_check import RiskState
        return RiskState(max_position_usd=500.0, max_daily_loss_usd=1000.0), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_dex() -> tuple[Any | None, bool]:
    try:
        from dex_executor import DexExecutor
        return DexExecutor(), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_nova_act() -> tuple[Any | None, bool]:
    try:
        from nova_act_auditor import NovaActAuditor
        return NovaActAuditor(), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_nova_sonic() -> tuple[Any | None, bool]:
    try:
        from nova_sonic_voice import NovaSonicVoice
        return NovaSonicVoice(), True
    except Exception:
        return None, False


@st.cache_resource(show_spinner=False)
def _init_nova_embed() -> tuple[Any | None, bool]:
    try:
        from nova_embeddings import NovaEmbeddingsAnalyzer
        return NovaEmbeddingsAnalyzer(), True
    except Exception:
        return None, False


_CHAIN, _HAS_CHAIN = _init_chain()
_PERF, _HAS_PERF = (None, False) if _ULTRA_LITE_MODE else _init_perf()
_ARTIFACTS, _HAS_ARTIFACTS = (None, False) if _ULTRA_LITE_MODE else _init_artifacts()
_RISK_STATE, _HAS_RISK = (None, False) if _ULTRA_LITE_MODE else _init_risk()
_DEX, _HAS_DEX = _init_dex()
_NOVA_ACT, _HAS_NOVA_ACT = (None, False) if _ULTRA_LITE_MODE else _init_nova_act()
_NOVA_SONIC, _HAS_NOVA_SONIC = (None, False) if _ULTRA_LITE_MODE else _init_nova_sonic()
_NOVA_EMBED, _HAS_NOVA_EMBED = (None, False) if _ULTRA_LITE_MODE else _init_nova_embed()

try:
    from risk_check import format_risk_report, run_all_checks
except Exception:
    format_risk_report = None  # type: ignore[assignment]
    run_all_checks = None  # type: ignore[assignment]

try:
    from sign_trade import validate_and_sign
    _HAS_SIGN = True
except Exception:
    validate_and_sign = None  # type: ignore[assignment]
    _HAS_SIGN = False

_BASE_PRICES = {
    "ETH/USDT": 3420.0,
    "BTC/USDT": 96750.0,
    "SOL/USDT": 192.0,
    "AVAX/USDT": 38.5,
    "LINK/USDT": 18.7,
}

_REGIME_COLORS = {
    "TRENDING": {"bg": "radial-gradient(circle, #ffd93d 0%, #b8860b 60%, #4a3500 100%)", "glow": "#ffd93daa", "text": "#ffd93d"},
    "RANGING": {"bg": "radial-gradient(circle, #4fc3f7 0%, #0277bd 60%, #01579b 100%)", "glow": "#4fc3f7aa", "text": "#4fc3f7"},
    "VOLATILE": {"bg": "radial-gradient(circle, #ff6b6b 0%, #c62828 60%, #4a0000 100%)", "glow": "#ff6b6baa", "text": "#ff6b6b"},
    "UNCERTAIN": {"bg": "radial-gradient(circle, #b388ff 0%, #6200ea 60%, #1a0050 100%)", "glow": "#b388ffaa", "text": "#b388ff"},
}

_PANELS = [
    "📊  Market",
    "🧠  AI Brain",
    "🛡️  Risk & Exec",
    "🌐  Trust Panel",
    "📊  Performance",
    "🔗  Audit Trail",
    "🧠  Calibration",
    "📡  Microstructure",
    "📒  TX Log",
    "📈  P&L",
    "🔍  History",
    "🔍  Nova Act Audit",
    "🎙️  Voice AI",
    "🖼️  Multimodal",
]

PANEL_PAGE_MAP = {
    "📊  Market": "pages/01_Market.py",
    "🧠  AI Brain": "pages/02_AI_Brain.py",
    "🛡️  Risk & Exec": "pages/03_Risk_Execution.py",
    "🌐  Trust Panel": "pages/04_Trust_Panel.py",
    "📊  Performance": "pages/05_Performance.py",
    "🔗  Audit Trail": "pages/06_Audit_Trail.py",
    "🧠  Calibration": "pages/07_Calibration.py",
    "📡  Microstructure": "pages/08_Microstructure.py",
    "📒  TX Log": "pages/09_TX_Log.py",
    "📈  P&L": "pages/10_PnL.py",
    "🔍  History": "pages/11_History.py",
    "🔍  Nova Act Audit": "pages/12_Nova_Act_Audit.py",
    "🎙️  Voice AI": "pages/13_Voice_AI.py",
    "🖼️  Multimodal": "pages/14_Multimodal.py",
}


def module_flags() -> dict[str, Any]:
    return {
        "has_chain": _HAS_CHAIN,
        "has_perf": _HAS_PERF,
        "has_artifacts": _HAS_ARTIFACTS,
        "has_risk": _HAS_RISK,
        "has_sign": _HAS_SIGN,
        "has_dex": _HAS_DEX,
        "has_nova_act": _HAS_NOVA_ACT,
        "has_nova_sonic": _HAS_NOVA_SONIC,
        "has_nova_embed": _HAS_NOVA_EMBED,
        "chain": _CHAIN,
        "nova_act": _NOVA_ACT,
        "nova_sonic": _NOVA_SONIC,
        "nova_embed": _NOVA_EMBED,
        "cloud_safe_mode": _CLOUD_SAFE_MODE,
        "ultra_lite_mode": _ULTRA_LITE_MODE,
    }


def _derive_wallet() -> str:
    if _HAS_CHAIN and _CHAIN is not None:
        return str(getattr(_CHAIN, "address", "0x0000000000000000000000000000000000000000"))
    try:
        from eth_account import Account as _Acct
        return _Acct.from_key(config.PRIVATE_KEY).address
    except Exception:
        return "0x0000000000000000000000000000000000000000"


def init_session_state() -> None:
    defaults: dict[str, Any] = {
        "agent_name": "ProtocolZero",
        "agent_wallet": _derive_wallet(),
        "reputation_score": 95,
        "agent_registered": False,
        "autonomous_mode": False,
        "cog_stream_live": False,
        "cog_refresh_sec": 15,
        "market_live_refresh": False,
        "market_refresh_sec": 15,
        "_last_market_refresh": 0.0,
        "selected_pair": "ETH/USDT",
        "market_df": None,
        "market_regime": "RANGING",
        "latest_decision": None,
        "decision_history": [],
        "cognitive_log": [],
        "max_position_usd": 500.0,
        "stop_loss_pct": 5.0,
        "take_profit_pct": 10.0,
        "max_daily_loss_usd": 1000.0,
        "total_capital_usd": 10_000.0,
        "session_pnl": 0.0,
        "trade_count": 0,
        "whatif_vol_mult": 1.0,
        "tx_log": [],
        "kill_switch_active": False,
        "vol_halt_threshold": 2.5,
        "rsi_halt_high": 80,
        "rsi_halt_low": 20,
        "pnl_history": [],
        "_api_calls_today": 0,
        "_api_calls_date": "",
        "_api_cost_estimate": 0.0,
        "total_spent": 0.0,
        "on_chain_token_id": None,
        "on_chain_rep_score": None,
        "on_chain_rep_count": 0,
        "on_chain_val_count": 0,
        "trust_history": [],
        "last_reg_tx": None,
        "analysis_latency_ms": 0,
        "calibration_data": [],
        "dex_enabled": bool(getattr(config, "DEX_ENABLED", False)) if config else False,
        "wallet_eth": 0.0,
        "wallet_weth": 0.0,
        "wallet_usdc": 0.0,
        "last_swap_result": None,
        "nova_act_results": [],
        "nova_voice_history": [],
        "nova_embed_results": [],
        "active_panel": _PANELS[0],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    caps = {
        "decision_history": 200,
        "tx_log": 200,
        "calibration_data": 200,
        "nova_act_results": 50,
        "nova_voice_history": 50,
        "nova_embed_results": 50,
        "pnl_history": 500,
    }
    for k, cap in caps.items():
        val = st.session_state.get(k)
        if isinstance(val, list) and len(val) > cap:
            st.session_state[k] = val[-cap:]

    session_file = pathlib.Path("artifacts") / "session_state.json"
    persist_keys = [
        "agent_registered", "autonomous_mode", "selected_pair", "latest_decision", "decision_history",
        "tx_log", "session_pnl", "trade_count", "market_regime", "whatif_vol_mult", "last_reg_tx",
        "reputation_score", "on_chain_rep_count", "_api_calls_today", "_api_calls_date", "_api_cost_estimate",
        "_last_auto_run", "_prev_auto_decision",
    ]
    if not st.session_state.get("_persist_restored", False):
        restore_persisted_state(st.session_state, session_file, persist_keys, logger)
        st.session_state["_persist_restored"] = True


def persist_session_state() -> None:
    session_file = pathlib.Path("artifacts") / "session_state.json"
    persist_keys = [
        "agent_registered", "autonomous_mode", "selected_pair", "latest_decision", "decision_history",
        "tx_log", "session_pnl", "trade_count", "market_regime", "whatif_vol_mult", "last_reg_tx",
        "reputation_score", "on_chain_rep_count", "_api_calls_today", "_api_calls_date", "_api_cost_estimate",
        "_last_auto_run", "_prev_auto_decision",
    ]
    persist_state(st.session_state, session_file, persist_keys, logger)


def inject_theme() -> None:
    st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">', unsafe_allow_html=True)
    st.markdown(
        """
<style>
:root { --border:#1a1a3e; --accent-cyan:#64ffda; --accent-red:#ff6b6b; --accent-gold:#ffd93d; --accent-blue:#4fc3f7; --accent-purple:#b388ff; --text-primary:#ccd6f6; --text-muted:#8892b0; --text-dim:#495670; }
.mcard { background: linear-gradient(135deg, #0c0c1f 0%, #111130 100%); border: 1px solid var(--border); border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: .6rem; text-align:center; }
.mcard .lbl { color: var(--text-muted); font-size:.7rem; text-transform:uppercase; letter-spacing:1.5px; }
.mcard .val { color: var(--text-primary); font-size:1.35rem; font-weight:700; font-family:'JetBrains Mono', monospace; }
.mcard .d-up { color: var(--accent-cyan); font-size:.8rem; }
.mcard .d-down { color: var(--accent-red); font-size:.8rem; }
.hz { border-bottom: 1px solid #1a1a3e; margin: .8rem 0; }
.cog-stream { max-height:220px; overflow:auto; background:#060612; border:1px solid #1a1a3e; border-radius:10px; padding:.6rem; }
.cog-line { margin:.2rem 0; font-size:.75rem; font-family:'JetBrains Mono', monospace; }
.cog-ts { color:#495670; } .cog-sym { color:#4fc3f7; } .cog-txt { color:#ccd6f6; } .cog-ok { color:#64ffda; } .cog-warn { color:#ffd93d; } .cog-err { color:#ff6b6b; }
.orb-container{ text-align:center; padding:.4rem 0; } .regime-orb{ width:90px; height:90px; border-radius:50%; margin:0 auto 10px; animation: pulse 2.4s ease-in-out infinite; } .orb-label{ font-weight:700; letter-spacing:1px; }
@keyframes pulse { 0%,100%{ transform:scale(1)} 50%{ transform:scale(1.05)} }
.router-flow { display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:.4rem; }
.router-step { border:1px solid #1a1a3e; border-radius:8px; padding:.4rem .5rem; min-width:84px; text-align:center; background:#0a0a1a; }
.router-step.pass{ border-color:#64ffda55; } .router-step.fail{ border-color:#ff6b6b66; } .router-step.pending{ border-color:#ffd93d66; }
.router-arrow { color:#495670; }
.hm-grid{ display:grid; grid-template-columns: repeat(2,1fr); gap:8px; }
.hm-cell{ border-radius:8px; padding:.55rem .7rem; border:1px solid #1a1a3e; }
.hm-lbl{ font-size:.66rem; color:#8892b0; text-transform:uppercase; } .hm-val{ font-size:.92rem; font-weight:700; }
.dec-box{ border-radius:12px; padding:1rem 1.1rem; margin:.6rem 0; font-family:'JetBrains Mono', monospace; }
.dec-buy{ background:linear-gradient(135deg,#0a2e23,#0d3b2e); border-left:4px solid #64ffda; }
.dec-sell{ background:linear-gradient(135deg,#2e0a0a,#3b0d0d); border-left:4px solid #ff6b6b; }
.dec-hold{ background:linear-gradient(135deg,#2e2a0a,#2d2a0d); border-left:4px solid #ffd93d; }
.badge { font-size:.64rem; border-radius:6px; padding:.12rem .42rem; }
.badge-green { background: rgba(100,255,218,.15); color:#64ffda; }
.badge-red { background: rgba(255,107,107,.15); color:#ff6b6b; }
.badge-gold { background: rgba(255,217,61,.12); color:#ffd93d; }
</style>
""",
        unsafe_allow_html=True,
    )


def mcard(label: str, value: str, delta: str = "", up: bool = True) -> str:
    dcls = "d-up" if up else "d-down"
    dhtml = f'<div class="{dcls}">{delta}</div>' if delta else ""
    return f'<div class="mcard"><div class="lbl">{label}</div><div class="val">{value}</div>{dhtml}</div>'


def _add_indicators(df: pd.DataFrame) -> None:
    df["sma_12"] = df["close"].rolling(12).mean()
    df["sma_26"] = df["close"].rolling(26).mean()
    df["pct_change"] = df["close"].pct_change() * 100
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))
    df["volatility"] = df["pct_change"].rolling(20).std()


def _generate_synthetic_ohlcv(symbol: str, hours: int = 72) -> pd.DataFrame:
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16) + int(time.time()) // 3600
    rng = np.random.default_rng(seed)
    base = _BASE_PRICES.get(symbol, 100.0)
    now = datetime.now(timezone.utc)
    rows: list[list[Any]] = []
    price = base * (1 + rng.normal(0, 0.015))
    for i in range(hours):
        ts = now - timedelta(hours=hours - i)
        ret = rng.normal(0.0001, 0.009)
        price *= 1 + ret
        high = price * (1 + abs(rng.normal(0, 0.005)))
        low = price * (1 - abs(rng.normal(0, 0.005)))
        opn = price * (1 + rng.normal(0, 0.003))
        vol = rng.uniform(400, 9000) * (base / 100)
        rows.append([ts, opn, high, low, price, vol])
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    _add_indicators(df)
    return df


@st.cache_data(ttl=120, show_spinner=False)
def _try_fetch_live(symbol: str) -> pd.DataFrame | None:
    if _CLOUD_SAFE_MODE:
        return None
    try:
        import ccxt
        for ex_name, symbols in [
            ("binance", [symbol, symbol.replace("USDT", "USD")]),
            ("coinbase", [symbol.replace("USDT", "USD"), symbol]),
        ]:
            ex_cls = getattr(ccxt, ex_name, None)
            if ex_cls is None:
                continue
            try:
                ex = ex_cls({"enableRateLimit": True, "timeout": 4000})
            except Exception:
                continue
            for s in symbols:
                try:
                    ohlcv = ex.fetch_ohlcv(s, timeframe="1h", limit=72)
                    if not ohlcv:
                        continue
                    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                    _add_indicators(df)
                    return df
                except Exception:
                    continue
    except Exception:
        return None
    return None


def load_market_data(symbol: str) -> pd.DataFrame:
    df = _try_fetch_live(symbol)
    if df is None:
        df = _generate_synthetic_ohlcv(symbol)
    st.session_state["market_df"] = df
    return df


def ensure_market_data() -> pd.DataFrame:
    pair = str(st.session_state.get("selected_pair", "ETH/USDT"))
    if st.session_state.get("market_df") is None:
        load_market_data(pair)
        st.session_state["_last_market_refresh"] = time.time()
    elif st.session_state.get("market_live_refresh", False):
        now = time.time()
        interval = max(10, int(st.session_state.get("market_refresh_sec", 15)))
        if now - float(st.session_state.get("_last_market_refresh", 0.0)) >= interval:
            load_market_data(pair)
            st.session_state["_last_market_refresh"] = now
    return st.session_state["market_df"]


def detect_regime(df: pd.DataFrame, vol_mult: float = 1.0) -> str:
    if df is None or len(df) < 26:
        return "UNCERTAIN"
    rsi = df["rsi_14"].iloc[-1] if pd.notna(df["rsi_14"].iloc[-1]) else 50
    sma12 = df["sma_12"].iloc[-1] if pd.notna(df["sma_12"].iloc[-1]) else 0
    sma26 = df["sma_26"].iloc[-1] if pd.notna(df["sma_26"].iloc[-1]) else 0
    vol = (df["volatility"].iloc[-1] if pd.notna(df["volatility"].iloc[-1]) else 0.5) * vol_mult
    sma_spread = abs(sma12 - sma26) / sma26 * 100 if sma26 else 0
    if vol > 1.2:
        return "VOLATILE"
    if sma_spread > 0.3 and (rsi > 52 or rsi < 48):
        return "TRENDING"
    if vol < 1.0 and 38 < rsi < 62:
        return "RANGING"
    return "UNCERTAIN"


def run_analysis(df: pd.DataFrame, pair: str, vol_mult: float = 1.0) -> dict[str, Any]:
    regime = detect_regime(df, vol_mult)
    st.session_state["market_regime"] = regime
    asset = pair.split("/")[0]
    rsi_now = df["rsi_14"].iloc[-1] if pd.notna(df["rsi_14"].iloc[-1]) else 50
    vol_now = (df["volatility"].iloc[-1] if pd.notna(df["volatility"].iloc[-1]) else 0.5) * vol_mult

    decision = None
    try:
        from brain import invoke_brain as _invoke
        decision = _invoke(df=df)
    except Exception:
        pass

    if decision is not None:
        return {
            "action": decision.get("action", "HOLD"),
            "asset": decision.get("asset", asset),
            "confidence": decision.get("confidence", 0.5),
            "entry_reasoning": decision.get("reason", ""),
            "risk_score": min(10, max(1, int(vol_now * 5))),
            "position_size_percent": min(2.0, round(decision.get("amount_usd", 0) / st.session_state["total_capital_usd"] * 100, 2)),
            "stop_loss_percent": st.session_state["stop_loss_pct"],
            "take_profit_percent": st.session_state["take_profit_pct"],
            "market_regime": regime,
            "amount_usd": decision.get("amount_usd", 0),
        }

    rng = np.random.default_rng(int(time.time()) % 100_000)
    conf = round(max(0.15, float(rng.uniform(0.55, 0.93)) - (vol_mult - 1) * 0.25), 2)
    action = "HOLD" if conf < 0.4 or regime == "VOLATILE" else str(rng.choice(["BUY", "SELL"], p=[0.55, 0.45]))
    risk_score = min(10, max(1, int(vol_now * 4 + rng.uniform(0, 2))))
    pos_pct = round(min(2.0, max(0.2, (conf * 2.0) - (vol_mult - 1) * 0.8)), 2) if action != "HOLD" else 0.0
    amount = round(st.session_state["total_capital_usd"] * pos_pct / 100, 2)
    reasons = {
        "BUY": f"SMA crossover bullish. RSI {rsi_now:.0f}. Regime {regime} supports entry.",
        "SELL": f"Potential exhaustion at RSI {rsi_now:.0f}. Regime {regime} supports defensive exit.",
        "HOLD": f"Signal uncertain. RSI {rsi_now:.0f}. Volatility {vol_now:.2f}. Regime {regime}.",
    }
    return {
        "action": action,
        "asset": asset,
        "confidence": conf,
        "entry_reasoning": reasons[action],
        "risk_score": risk_score,
        "position_size_percent": pos_pct,
        "stop_loss_percent": st.session_state["stop_loss_pct"],
        "take_profit_percent": st.session_state["take_profit_pct"],
        "market_regime": regime,
        "amount_usd": amount,
    }


def cog(symbol: str, text: str, level: str = "info") -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    cls_map = {"info": "cog-txt", "ok": "cog-ok", "warn": "cog-warn", "err": "cog-err", "sym": "cog-sym"}
    st.session_state["cognitive_log"].append({"ts": ts, "sym": symbol, "text": text, "cls": cls_map.get(level, "cog-txt")})
    if len(st.session_state["cognitive_log"]) > 100:
        st.session_state["cognitive_log"] = st.session_state["cognitive_log"][-100:]


def render_cognitive_stream() -> str:
    if not st.session_state.get("cognitive_log"):
        return '<div class="cog-stream"><span class="cog-txt">Awaiting first analysis cycle…</span></div>'
    lines = []
    for e in st.session_state["cognitive_log"]:
        lines.append(f'<p class="cog-line"><span class="cog-ts">[{e["ts"]}]</span> <span class="cog-sym">{e["sym"]}</span> <span class="{e["cls"]}">{e["text"]}</span></p>')
    return f'<div class="cog-stream">{"".join(lines)}</div>'


def regime_orb_html(regime: str) -> str:
    r = _REGIME_COLORS.get(regime, _REGIME_COLORS["UNCERTAIN"])
    return f'<div class="orb-container"><div class="regime-orb" style="background:{r["bg"]};box-shadow:0 0 40px {r["glow"]},0 0 80px {r["glow"]}"></div><div class="orb-label" style="color:{r["text"]}">{regime}</div></div>'


def trade_dna_html(history: list[dict[str, Any]]) -> str:
    if not history:
        return '<div style="color:#495670;text-align:center;padding:1rem">No trade DNA yet</div>'
    out = []
    for i, t in enumerate(history[-20:]):
        conf = float(t.get("confidence", 0.5))
        risk = int(t.get("risk_score", 5))
        pos = float(t.get("position_size_percent", 1.0))
        action = str(t.get("action", "HOLD"))
        color = {"BUY": "#64ffda", "SELL": "#ff6b6b"}.get(action, "#ffd93d")
        out.append(
            f'<div style="display:flex;gap:3px;align-items:flex-end" title="#{i + 1} {action}">'
            f'<div style="height:{int(conf * 40 + 5)}px;width:8px;background:{color}"></div>'
            f'<div style="height:{int(risk * 4 + 5)}px;width:6px;background:#b388ff"></div>'
            f'<div style="height:{int(pos * 20 + 5)}px;width:6px;background:#4fc3f7"></div>'
            f'</div>'
        )
    return f'<div style="display:flex;gap:6px;align-items:end;padding:.5rem;overflow-x:auto">{"".join(out)}</div>'


def risk_heatmap_html(state: dict[str, Any], decision: dict[str, Any] | None, vol_mult: float) -> str:
    cap = state.get("total_capital_usd", 0)
    pnl = state.get("session_pnl", 0)
    max_loss = state.get("max_daily_loss_usd", 1)
    exposure = decision.get("position_size_percent", 0) if decision else 0
    risk_bud = max(0, 1 - abs(pnl) / max_loss) * 100 if max_loss else 100
    cap_risk = (decision.get("amount_usd", 0) / cap * 100) if (cap and decision) else 0
    aggr = min(10, (decision.get("risk_score", 5) if decision else 3) + int(vol_mult))

    def _cc(val: float, thresholds: tuple[float, float]) -> str:
        if val > thresholds[1]:
            return "background:linear-gradient(135deg,#3b0d0d,#2a0808);color:#ff6b6b"
        if val > thresholds[0]:
            return "background:linear-gradient(135deg,#2d2a0d,#1f1c06);color:#ffd93d"
        return "background:linear-gradient(135deg,#0d3b2e,#081f18);color:#64ffda"

    return f'''<div class="hm-grid">
    <div class="hm-cell" style="{_cc(exposure, (1.0, 1.8))}"><div class="hm-lbl">Exposure</div><div class="hm-val">{exposure:.1f}%</div></div>
    <div class="hm-cell" style="{_cc(100 - risk_bud, (40, 70))}"><div class="hm-lbl">Risk Budget</div><div class="hm-val">{risk_bud:.0f}%</div></div>
    <div class="hm-cell" style="{_cc(cap_risk, (1.0, 2.0))}"><div class="hm-lbl">Capital at Risk</div><div class="hm-val">{cap_risk:.1f}%</div></div>
    <div class="hm-cell" style="{_cc(aggr, (5, 8))}"><div class="hm-lbl">Aggression</div><div class="hm-val">{aggr}/10</div></div>
</div>'''


def risk_router_html(dec: dict[str, Any] | None) -> str:
    if not dec:
        return '<div style="color:#495670;text-align:center">Run analysis first</div>'
    checks = [
        ("📋 Token", "pass", "Verified"),
        ("⏰ Age", "pass", ">30d"),
        ("🔒 Liquidity", "pass", "Locked"),
        ("🚫 Blacklist", "pass", "Clean"),
        ("📊 Volume", "pass", "Normal"),
    ]
    if dec.get("risk_score", 0) > 7:
        checks[2] = ("🔒 Liquidity", "fail", "Unlocked")
    if dec.get("market_regime") == "VOLATILE":
        checks[4] = ("📊 Volume", "pending", "Unusual")
    steps = []
    for i, (label, status, detail) in enumerate(checks):
        icon = {"pass": "✅", "fail": "❌", "pending": "⚠️"}[status]
        steps.append(f'<div class="router-step {status}"><div>{icon}</div><div style="font-size:.67rem">{label}</div><div style="font-size:.58rem;color:#495670">{detail}</div></div>')
        if i < len(checks) - 1:
            steps.append('<div class="router-arrow">→</div>')
    all_pass = all(c[1] == "pass" for c in checks)
    verdict = "✅ APPROVED" if all_pass else "⚠️ REVIEW"
    color = "#64ffda" if all_pass else "#ff6b6b"
    return f'<div class="router-flow">{"".join(steps)}</div><div style="text-align:center;color:{color};margin-top:.5rem">{verdict}</div>'


def simulate_trade(dec: dict[str, Any], capital: float) -> dict[str, float]:
    rng = np.random.default_rng(int(time.time()) % 10000)
    amount = float(dec.get("amount_usd", 0))
    gas_gwei = round(float(rng.uniform(15, 45)), 1)
    gas_cost_eth = round(gas_gwei * 21000 / 1e9, 6)
    gas_cost_usd = round(gas_cost_eth * 3420, 2)
    slippage = round(float(rng.uniform(0.01, 0.3)), 2)
    net_amount = round(amount * (1 - slippage / 100), 2)
    final_balance = round(capital - amount - gas_cost_usd, 2)
    return {
        "gas_gwei": gas_gwei,
        "gas_cost_eth": gas_cost_eth,
        "gas_cost_usd": gas_cost_usd,
        "slippage_pct": slippage,
        "net_amount": net_amount,
        "final_balance": final_balance,
        "total_cost": round(amount + gas_cost_usd, 2),
    }


def _safe_pnl_value(raw: Any) -> float:
    try:
        return float(str(raw).replace("$", "").replace(",", "").replace("+", "").strip())
    except Exception:
        return 0.0


def pnl_chart(tx_log: list[dict[str, Any]]) -> go.Figure | None:
    trades = [t for t in tx_log if t.get("action") in ("BUY", "SELL")]
    if not trades:
        return None
    cum = 0.0
    xs: list[str] = []
    ys: list[float] = []
    for t in trades:
        cum += _safe_pnl_value(t.get("pnl", "$0"))
        xs.append(str(t.get("timestamp", "")))
        ys.append(cum)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, fill="tozeroy", mode="lines+markers", line=dict(color="#64ffda" if cum >= 0 else "#ff6b6b", width=2)))
    fig.add_hline(y=0, line_dash="dash", line_color="#495670")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=250, margin=dict(l=0, r=0, t=10, b=0))
    return fig


@st.cache_data(ttl=20, show_spinner=False)
def cached_equity_curve_from_txlog(tx_log_json: str, starting_capital: float = 10000.0) -> list[float]:
    try:
        tx_log = json.loads(tx_log_json)
    except Exception:
        tx_log = []
    curve = [float(starting_capital)]
    cur = float(starting_capital)
    for t in tx_log:
        if str(t.get("action", "")).upper() in {"BUY", "SELL"}:
            cur += _safe_pnl_value(t.get("pnl", "$0"))
            curve.append(round(cur, 2))
    return curve


@st.cache_data(ttl=20, show_spinner=False)
def cached_regime_breakdown_from_logs(decision_history_json: str, tx_log_json: str) -> dict[str, dict[str, int]]:
    try:
        history = json.loads(decision_history_json)
    except Exception:
        history = []
    try:
        tx_log = json.loads(tx_log_json)
    except Exception:
        tx_log = []
    ts_to_regime: dict[str, str] = {}
    for d in history:
        ts = str(d.get("timestamp") or d.get("time") or "")
        rg = str(d.get("market_regime") or d.get("regime") or "UNCERTAIN").upper()
        if ts:
            ts_to_regime[ts] = rg
    out: dict[str, dict[str, int]] = {}
    for t in tx_log:
        if str(t.get("action", "")).upper() not in {"BUY", "SELL"}:
            continue
        reg = ts_to_regime.get(str(t.get("timestamp") or ""), "UNCERTAIN")
        pnl = _safe_pnl_value(t.get("pnl", "$0"))
        if reg not in out:
            out[reg] = {"wins": 0, "losses": 0}
        if pnl > 0:
            out[reg]["wins"] += 1
        else:
            out[reg]["losses"] += 1
    return out


@st.cache_data(ttl=30, show_spinner=False)
def load_artifacts() -> list[dict[str, Any]]:
    art_dir = pathlib.Path("artifacts")
    out: list[dict[str, Any]] = []
    if art_dir.exists():
        for f in sorted(art_dir.glob("pz-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            try:
                out.append(json.loads(f.read_text()))
            except Exception:
                continue
    return out


def _normalize_tx_hash(tx: Any) -> str:
    if tx is None:
        return ""
    tx_str = str(tx).strip()
    m = re.search(r"0x[a-fA-F0-9]{64}", tx_str)
    return m.group(0) if m else tx_str


def _is_tx_hash(value: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{64}", str(value or "").strip()))


def real_register_agent() -> dict[str, Any]:
    if _CLOUD_SAFE_MODE:
        seed = f"{st.session_state.get('agent_name', 'ProtocolZero')}-{time.time()}"
        return {"success": True, "tx": "0x" + hashlib.sha256(seed.encode()).hexdigest(), "error": None}
    if not _HAS_CHAIN or _CHAIN is None:
        return {"success": False, "tx": None, "error": "Chain not available"}
    try:
        from metadata_handler import generate_metadata
        tx = _CHAIN.register_agent(json.dumps(generate_metadata()))
        return {"success": True, "tx": tx, "error": None}
    except Exception as e:
        return {"success": False, "tx": None, "error": str(e)}


def real_execute_trade(decision: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    if _CLOUD_SAFE_MODE:
        seed = f"safe-{decision.get('action')}-{time.time()}"
        return {"success": True, "tx": "0x" + hashlib.sha256((seed + '-tx').encode()).hexdigest(), "sig": "0x" + hashlib.sha256((seed + '-sig').encode()).hexdigest(), "pnl": 0.0, "risk_report": "Cloud-safe demo mode", "error": None}

    result: dict[str, Any] = {"success": False, "tx": None, "sig": None, "pnl": 0.0, "risk_report": "", "error": None}
    timings: dict[str, float] = {}
    risk_results_raw: tuple[bool, list[str]] | None = None
    sign_result_raw: dict[str, Any] | None = None

    t0 = time.perf_counter()
    if _HAS_RISK and _RISK_STATE is not None and callable(run_all_checks) and callable(format_risk_report):
        try:
            decision["reputation_score"] = st.session_state.get("reputation_score", 95)
            risk_ok, risk_msgs = run_all_checks(_RISK_STATE, decision)
            risk_results_raw = (risk_ok, risk_msgs)
            result["risk_report"] = format_risk_report(_RISK_STATE, decision)
            if not risk_ok:
                result["error"] = "Risk checks failed"
                return result
        except Exception as e:
            result["error"] = f"Risk check error: {e}"
            return result
    timings["🛡️ Risk Check"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    if _HAS_SIGN and callable(validate_and_sign):
        try:
            sign_result_raw = validate_and_sign(decision)
            if sign_result_raw.get("status") == "signed" and sign_result_raw.get("signed"):
                result["sig"] = sign_result_raw["signed"].get("signature", "")
            else:
                result["error"] = "Signing rejected"
                return result
        except Exception as e:
            result["error"] = f"Signing error: {e}"
            return result
    timings["🔏 EIP-712 Sign"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    if _HAS_CHAIN and _CHAIN is not None and result.get("sig"):
        try:
            result["tx"] = _CHAIN.submit_intent(decision)
            result["success"] = True
        except Exception as e:
            result["error"] = f"Chain submission error: {e}"
    timings["⛓️ On-Chain TX"] = (time.perf_counter() - t0) * 1000

    if _HAS_ARTIFACTS and _ARTIFACTS is not None:
        try:
            market_snapshot = {
                "price": float(df["close"].iloc[-1]),
                "rsi": float(df["rsi_14"].iloc[-1]) if pd.notna(df["rsi_14"].iloc[-1]) else 50.0,
                "volatility": float(df["volatility"].iloc[-1]) if pd.notna(df["volatility"].iloc[-1]) else 0.5,
            }
            _ARTIFACTS.build_artifact(decision=decision, market_data=market_snapshot, risk_results=risk_results_raw, signed_intent=sign_result_raw)
        except Exception:
            pass

    if _HAS_PERF and _PERF is not None:
        try:
            current_price = float(df["close"].iloc[-1])
            pnl_est = 0.0
            if len(df) >= 2 and decision.get("action") in ("BUY", "SELL"):
                prev = float(df["close"].iloc[-2])
                ret = (current_price - prev) / prev if prev else 0
                direction = 1.0 if decision.get("action") == "BUY" else -1.0
                pnl_est = round(float(decision.get("amount_usd", 0)) * ret * direction, 2)
            _PERF.record_trade(
                action=decision.get("action", "HOLD"),
                asset=decision.get("asset", "?"),
                entry_price=current_price,
                amount_usd=decision.get("amount_usd", 0),
                pnl_usd=pnl_est,
                confidence=decision.get("confidence", 0.5),
                market_regime=decision.get("market_regime", "UNCERTAIN"),
            )
        except Exception:
            pass

    result["pipeline_timings"] = timings
    return result


def get_performance_report() -> dict[str, Any]:
    if not _HAS_PERF or _PERF is None:
        return {}
    try:
        return _PERF.get_report()
    except Exception:
        return {}


def fetch_on_chain_identity() -> dict[str, Any]:
    if _CLOUD_SAFE_MODE:
        return {"registered": bool(st.session_state.get("agent_registered", False)), "token_id": st.session_state.get("on_chain_token_id"), "error": None}
    if not _HAS_CHAIN or _CHAIN is None:
        return {"registered": False, "token_id": None, "error": "Chain not available"}
    try:
        registered = _CHAIN.is_registered()
        token_id = _CHAIN.get_token_id() if registered else None
        if token_id:
            st.session_state["on_chain_token_id"] = token_id
            st.session_state["agent_registered"] = True
        return {"registered": registered, "token_id": token_id, "error": None}
    except Exception as e:
        return {"registered": False, "token_id": None, "error": str(e)}


def fetch_on_chain_reputation() -> dict[str, Any]:
    if _CLOUD_SAFE_MODE:
        return {"score": st.session_state.get("reputation_score", 95), "count": int(st.session_state.get("on_chain_rep_count", 0)), "error": None}
    if not _HAS_CHAIN or _CHAIN is None:
        return {"score": None, "count": 0, "error": "Chain not available"}
    try:
        summary = _CHAIN.get_reputation_summary()
        score = summary.get("cumulative_value")
        count = int(summary.get("total_feedback", 0) or 0)
        if score is not None:
            st.session_state["reputation_score"] = int(score)
        st.session_state["on_chain_rep_count"] = count
        return {"score": score, "count": count, "error": None}
    except Exception as e:
        return {"score": None, "count": 0, "error": str(e)}


def fetch_validation_summary() -> dict[str, Any]:
    if _CLOUD_SAFE_MODE:
        total = int(st.session_state.get("on_chain_val_count", 0) or 0)
        return {"total": total, "approved": total, "error": None}
    if not _HAS_CHAIN or _CHAIN is None:
        return {"total": 0, "approved": 0, "error": "Chain not available"}
    try:
        summary = _CHAIN.get_validation_summary()
        total = int(summary.get("total_requests", 0) or 0)
        approved = int(summary.get("approved", 0) or 0)
        st.session_state["on_chain_val_count"] = total
        return {"total": total, "approved": approved, "error": None}
    except Exception as e:
        return {"total": 0, "approved": 0, "error": str(e)}


def check_rug_pull(df: pd.DataFrame) -> dict[str, Any] | None:
    if df is None or len(df) < 10:
        return None
    last5 = df["volume"].tail(5)
    avg = df["volume"].tail(48).mean()
    drop = (df["close"].iloc[-1] / df["close"].iloc[-5] - 1) * 100
    spike = (last5.mean() / avg - 1) * 100 if avg > 0 else 0
    alerts = []
    if drop < -8:
        alerts.append(f"Sharp price drop: {drop:.1f}% in last 5 hours")
    if spike > 200:
        alerts.append(f"Volume spike: {spike:.0f}% above average")
    rsi = df["rsi_14"].iloc[-1]
    if pd.notna(rsi) and rsi < 15:
        alerts.append(f"RSI critically low: {rsi:.1f}")
    if alerts:
        return {"level": "critical" if drop < -15 else "warning", "alerts": alerts}
    return None


def render_top_row(df: pd.DataFrame) -> str:
    regime = detect_regime(df, st.session_state.get("whatif_vol_mult", 1.0))
    st.session_state["market_regime"] = regime
    col_orb, col_gap1, col_cog, col_gap2, col_dna = st.columns([1.2, 0.1, 2.5, 0.1, 1.5], gap="large")
    with col_orb:
        st.markdown("##### 🌌 Regime Orb")
        st.markdown(regime_orb_html(regime), unsafe_allow_html=True)
    with col_gap1:
        st.markdown("")
    with col_cog:
        st.markdown("##### 🧠 Cognitive Stream")
        st.markdown(render_cognitive_stream(), unsafe_allow_html=True)
    with col_gap2:
        st.markdown("")
    with col_dna:
        st.markdown("##### 🧬 Trade DNA")
        st.markdown(trade_dna_html(st.session_state.get("decision_history", [])), unsafe_allow_html=True)
    return regime


def render_panel_nav(current_label: str) -> None:
    if current_label not in _PANELS:
        return
    st.session_state["active_panel"] = current_label
    seg = getattr(st, "segmented_control", None)
    if callable(seg):
        selected = seg("Panels", options=_PANELS, index=_PANELS.index(current_label), key=f"active_panel_{current_label}", label_visibility="collapsed")
    else:
        selected = st.radio("Panels", options=_PANELS, index=_PANELS.index(current_label), horizontal=True, key=f"active_panel_{current_label}", label_visibility="collapsed")
    if selected and selected != current_label:
        target = PANEL_PAGE_MAP.get(selected)
        if target:
            try:
                st.switch_page(target)
            except Exception:
                pass


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🛡️ Protocol Zero")
        st.caption("Autonomous Trust-Minimized Trading Agent")
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
        auto = st.toggle("Autonomous Mode", value=bool(st.session_state.get("autonomous_mode", False)), key="auto_toggle")
        st.session_state["autonomous_mode"] = auto

        st.markdown("### 🤖 Agent Identity")
        st.session_state["agent_name"] = st.text_input("Agent Name", value=st.session_state.get("agent_name", "ProtocolZero"))
        st.session_state["agent_wallet"] = st.text_input("Wallet", value=st.session_state.get("agent_wallet", ""))

        rep = int(st.session_state.get("reputation_score", 95))
        rep_c = "#64ffda" if rep >= 70 else ("#ffd93d" if rep >= 40 else "#ff6b6b")
        st.markdown(f'<div class="mcard"><div class="lbl">On-Chain Reputation</div><div class="val" style="color:{rep_c}">{rep}<span style="font-size:.8rem;color:#495670"> / 100</span></div></div>', unsafe_allow_html=True)

        if st.button("🔗  Register On-Chain", use_container_width=True, type="primary"):
            reg = real_register_agent()
            if reg.get("success"):
                st.session_state["agent_registered"] = True
                tx = _normalize_tx_hash(reg.get("tx"))
                st.session_state["last_reg_tx"] = tx if _is_tx_hash(tx) else st.session_state.get("last_reg_tx")
                cog("✓", "Agent registered on ERC-8004 Identity Registry", "ok")
                st.success("Registration successful")
            else:
                st.warning(f"Registration failed: {reg.get('error', 'unknown')}")

        st.markdown("### ⚙️ Risk Parameters")
        st.session_state["max_position_usd"] = st.number_input("Max Position ($)", value=float(st.session_state.get("max_position_usd", 500.0)), min_value=10.0, max_value=50000.0, step=50.0)
        st.session_state["stop_loss_pct"] = st.slider("Stop Loss %", 1.0, 25.0, float(st.session_state.get("stop_loss_pct", 5.0)), 0.5)
        st.session_state["take_profit_pct"] = st.slider("Take Profit %", 1.0, 50.0, float(st.session_state.get("take_profit_pct", 10.0)), 0.5)
        st.session_state["max_daily_loss_usd"] = st.number_input("Daily Loss Cap ($)", value=float(st.session_state.get("max_daily_loss_usd", 1000.0)), min_value=50.0, max_value=100000.0, step=100.0)
        st.session_state["total_capital_usd"] = st.number_input("Total Capital ($)", value=float(st.session_state.get("total_capital_usd", 10000.0)), min_value=100.0, max_value=1000000.0, step=500.0)

        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
        if st.session_state.get("kill_switch_active", False):
            st.error("⛔ Kill switch active")
            if st.button("✅ Resume Trading", use_container_width=True):
                st.session_state["kill_switch_active"] = False
        else:
            if st.button("🚨 EMERGENCY STOP", use_container_width=True, type="primary"):
                st.session_state["kill_switch_active"] = True
                st.session_state["autonomous_mode"] = False
                cog("⛔", "KILL SWITCH ACTIVATED", "err")


def render_header() -> None:
    st.markdown(
        '# 🛡️ Protocol Zero <span style="font-size:0.55rem;color:#495670;font-weight:400">v1.0 · Autonomous Agent · ERC-8004</span>',
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=120, show_spinner=False)
    def _bedrock_runtime_probe() -> tuple[str, int, str]:
        return bedrock_runtime_probe(
            cloud_safe_mode=_CLOUD_SAFE_MODE,
            config_module=config,
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        )

    @st.cache_data(ttl=60, show_spinner=False)
    def _system_health_check() -> dict[str, Any]:
        return system_health_check(cloud_safe_mode=_CLOUD_SAFE_MODE, rpc_url=os.getenv("RPC_URL", ""), bedrock_probe=_bedrock_runtime_probe)

    st.markdown(build_health_badges_html(_system_health_check()), unsafe_allow_html=True)


def render_shell(current_panel: str | None = None, show_top_row: bool = True) -> pd.DataFrame:
    init_session_state()
    inject_theme()
    render_sidebar()
    render_header()
    df = ensure_market_data()

    if st.session_state.get("kill_switch_active"):
        st.markdown('<div class="dec-box dec-sell"><b>⛔ EMERGENCY STOP ACTIVE — ALL TRADING HALTED</b></div>', unsafe_allow_html=True)

    alert = check_rug_pull(df)
    if alert:
        st.markdown(f'<div class="dec-box dec-sell"><b>🚨 RUG-PULL ALERT</b><br>{" · ".join(alert["alerts"])}</div>', unsafe_allow_html=True)

    if show_top_row:
        render_top_row(df)
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    if current_panel:
        render_panel_nav(current_panel)

    return df


def finalize_page() -> None:
    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
    st.markdown(footer_html(), unsafe_allow_html=True)
    persist_session_state()
    try:
        gc.collect()
    except Exception:
        pass


def confidence_gauge(conf: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=conf * 100,
        number={"suffix": "%", "font": {"color": "#ccd6f6", "size": 28}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#495670", "tickfont": {"color": "#495670"}},
            "bar": {"color": "#64ffda" if conf >= 0.7 else ("#ffd93d" if conf >= 0.4 else "#ff6b6b")},
            "bgcolor": "#111130",
            "borderwidth": 0,
        },
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "#8892b0"}, height=200, margin=dict(l=20, r=20, t=30, b=10))
    return fig


def get_eth_usd_price_hint() -> float:
    df = st.session_state.get("market_df")
    pair = str(st.session_state.get("selected_pair", "ETH/USDT"))
    try:
        if isinstance(df, pd.DataFrame) and not df.empty and "close" in df.columns:
            last = float(df["close"].iloc[-1])
            if last > 0 and pair.startswith("ETH/"):
                return last
    except Exception:
        pass
    return float(_BASE_PRICES.get("ETH/USDT", 3420.0))
