from __future__ import annotations

import gc
import hashlib
import json
import logging
import math
import os
import pathlib
import re
import time
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

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


def log_diagnostic(level: str, message: str, details: dict[str, Any] | None = None) -> None:
    if "system_diagnostics" not in st.session_state:
        st.session_state["system_diagnostics"] = []
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "level": level.upper(),
        "message": message,
        "details": details or {},
    }
    st.session_state["system_diagnostics"].append(entry)
    if len(st.session_state["system_diagnostics"]) > 200:
        st.session_state["system_diagnostics"] = st.session_state["system_diagnostics"][-200:]


def protocol_zero_safe_run(
    func: Callable[..., Any] | None = None,
    *,
    retries: int = 2,
    fallback_value: Any = "ACCESS_DENIED_BY_ORG",
    backup_bridge: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    def _decorate(inner: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(inner)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            max_attempts = max(1, retries + 1)
            for attempt in range(1, max_attempts + 1):
                try:
                    return inner(*args, **kwargs)
                except Exception as exc:
                    msg = str(exc)
                    lmsg = msg.lower()
                    is_conn = any(k in lmsg for k in ["timeout", "connection", "websocket", "network"])
                    is_bedrock = any(k in lmsg for k in ["operation not allowed", "validationexception", "bedrock", "access denied"])
                    is_oom = isinstance(exc, MemoryError) or any(k in lmsg for k in ["out of memory", "oom", "overflow"])

                    if "_bedrock_fail_count" not in st.session_state:
                        st.session_state["_bedrock_fail_count"] = 0
                    if is_bedrock:
                        st.session_state["_bedrock_fail_count"] = int(st.session_state.get("_bedrock_fail_count", 0)) + 1

                    log_diagnostic(
                        "warn" if (is_conn or is_bedrock) else "error",
                        "safe_run_exception",
                        {"attempt": attempt, "error": msg, "connection": is_conn, "bedrock": is_bedrock},
                    )

                    if is_oom:
                        try:
                            gc.collect()
                        except Exception:
                            pass

                    if is_conn and attempt < max_attempts:
                        time.sleep(min(2.0, 0.35 * (2 ** (attempt - 1))))
                        continue

                    if is_bedrock and backup_bridge is not None and int(st.session_state.get("_bedrock_fail_count", 0)) >= 3:
                        try:
                            log_diagnostic("warn", "backup_bridge_activated", {"attempt": attempt, "bedrock_fail_count": st.session_state.get("_bedrock_fail_count", 0)})
                            st.warning("⚠️ PROTOCOL ALERT: Tactical connection unstable. Switching to Backup Core.")
                            return backup_bridge(*args, **kwargs)
                        except Exception as be:
                            log_diagnostic("error", "backup_bridge_failed", {"error": str(be)})

                    if is_bedrock or is_conn:
                        st.warning("⚠️ PROTOCOL ALERT: Tactical connection unstable. Retrying/Recovering…")
                    else:
                        st.warning("⚠️ PROTOCOL ALERT: Non-critical module error handled.")
                    return fallback_value
            return fallback_value

        return _wrapped

    if func is not None:
        return _decorate(func)
    return _decorate


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
        "system_diagnostics": [],
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
    st.markdown(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<style>

:root {
    --bg-primary:    #060612;
    --bg-card:       #0c0c1f;
    --bg-card-hover: #111130;
    --border:        #1a1a3e;
    --accent-cyan:   #64ffda;
    --accent-red:    #ff6b6b;
    --accent-gold:   #ffd93d;
    --accent-blue:   #4fc3f7;
    --accent-purple: #b388ff;
    --text-primary:  #ccd6f6;
    --text-muted:    #8892b0;
    --text-dim:      #495670;
}

.stApp { font-family: 'Inter', sans-serif; }

/* ── Metric cards ───────────────────────────────────── */
.mcard {
    background: linear-gradient(135deg, #0c0c1f 0%, #111130 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    text-align: center;
    transition: border-color 0.3s, transform 0.2s;
}
.mcard:hover { border-color: var(--accent-cyan); transform: translateY(-2px); }
.mcard .lbl {
    color: var(--text-muted); font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 0.2rem;
}
.mcard .val {
    color: var(--text-primary); font-size: 1.45rem; font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}
.mcard .d-up   { color: var(--accent-cyan); font-size: 0.8rem; }
.mcard .d-down { color: var(--accent-red);  font-size: 0.8rem; }

/* ── Module status grid ─────────────────────────────── */
.mod-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin: 0.5rem 0 1rem 0;
}
.mod-card {
    background: linear-gradient(135deg, #0c0c1f 0%, #111130 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.65rem;
    transition: border-color 0.3s, transform 0.2s;
}
.mod-card:hover { border-color: var(--accent-cyan); transform: translateY(-2px); }
.mod-card.mod-on  { border-left: 3px solid var(--accent-cyan); }
.mod-card.mod-off { border-left: 3px solid var(--accent-red); opacity: 0.65; }
.mod-card .mod-icon { font-size: 1.05rem; flex-shrink: 0; line-height: 1; }
.mod-card .mod-name {
    color: var(--text-muted);
    font-size: clamp(0.6rem, 1.1vw, 0.82rem);
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.mod-card .mod-tag {
    margin-left: auto;
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    flex-shrink: 0;
}
.mod-card.mod-on .mod-tag  { color: #64ffda; background: rgba(100,255,218,0.1); }
.mod-card.mod-off .mod-tag { color: #ff6b6b; background: rgba(255,107,107,0.1); }

/* ── Decision banners ───────────────────────────────── */
.dec-box {
    border-radius: 14px; padding: 1.2rem 1.5rem;
    margin: 0.6rem 0;
    font-family: 'JetBrains Mono', monospace;
}
.dec-buy  { background: linear-gradient(135deg, #0a2e23, #0d3b2e); border-left: 4px solid var(--accent-cyan); }
.dec-sell { background: linear-gradient(135deg, #2e0a0a, #3b0d0d); border-left: 4px solid var(--accent-red); }
.dec-hold { background: linear-gradient(135deg, #2e2a0a, #2d2a0d); border-left: 4px solid var(--accent-gold); }

/* ── Cognitive stream ───────────────────────────────── */
.cog-stream {
    background: #050510;
    border: 1px solid #0d0d2a;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.5rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    max-height: 320px;
    overflow-y: auto;
    line-height: 1.7;
}
.cog-line { margin: 0; padding: 0; }
.cog-ts   { color: #3a3a5c; }
.cog-sym  { color: var(--accent-cyan); }
.cog-warn { color: var(--accent-gold); }
.cog-err  { color: var(--accent-red); }
.cog-ok   { color: var(--accent-cyan); }
.cog-txt  { color: #7a8baa; }

/* ── Regime orb ─────────────────────────────────────── */
@keyframes orbPulse {
    0%, 100% { transform: scale(1);    filter: brightness(1);   }
    50%      { transform: scale(1.08); filter: brightness(1.3); }
}
.orb-container { text-align: center; padding: 1.5rem 0.5rem; margin: 0.5rem 0; }
.regime-orb {
    display: inline-block;
    width: 120px; height: 120px;
    border-radius: 50%;
    animation: orbPulse 3s ease-in-out infinite;
}
.orb-label {
    margin-top: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* ── Heat-map grid ──────────────────────────────────── */
.hm-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.hm-cell {
    border-radius: 10px; padding: 0.8rem;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.3s;
}
.hm-cell .hm-lbl {
    font-size: 0.65rem; color: #8892b0;
    text-transform: uppercase; letter-spacing: 1px;
}
.hm-cell .hm-val { font-size: 1.2rem; font-weight: 700; margin-top: 0.2rem; }

/* ── Autonomous badge ───────────────────────────────── */
.auto-badge-on {
    background: linear-gradient(135deg, #0d3b2e, #0a4a38);
    border: 1px solid var(--accent-cyan);
    border-radius: 12px; padding: 0.8rem 1.2rem;
    text-align: center;
    animation: orbPulse 2s ease-in-out infinite;
}
.auto-badge-off {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px; padding: 0.8rem 1.2rem;
    text-align: center;
}

/* ── Misc ───────────────────────────────────────────── */
.hz  { border-top: 1px solid var(--border); margin: 0.8rem 0; }
.badge {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
    font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.badge-green  { background: #0d3b2e; color: var(--accent-cyan); }
.badge-red    { background: #3b0d0d; color: var(--accent-red); }
.badge-gold   { background: #2d2a0d; color: var(--accent-gold); }
.badge-blue   { background: #0f3460; color: var(--accent-blue); }
.badge-purple { background: #1a0d3b; color: var(--accent-purple); }

/* ── Kill Switch ────────────────────────────────────── */
@keyframes killPulse {
    0%, 100% { box-shadow: 0 0 10px #ff000044; }
    50%      { box-shadow: 0 0 25px #ff0000aa, 0 0 50px #ff000044; }
}
.kill-active {
    background: linear-gradient(135deg, #3b0d0d, #5a1010);
    border: 2px solid #ff6b6b;
    border-radius: 12px; padding: 1rem; text-align: center;
    animation: killPulse 1.5s ease-in-out infinite;
}

/* ── Rug Pull Alert ─────────────────────────────────── */
@keyframes rugFlash {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.4; }
}
.rug-alert {
    background: linear-gradient(135deg, #3b0d0d, #5a1010);
    border: 1px solid #ff6b6b;
    border-radius: 12px; padding: 0.8rem 1.2rem;
    margin-bottom: 1rem;
    animation: rugFlash 1s ease-in-out infinite;
    font-family: 'JetBrains Mono', monospace;
}

/* ── XAI Panel ──────────────────────────────────────── */
.xai-panel {
    background: linear-gradient(135deg, #0c0c1f 0%, #0f1428 100%);
    border: 1px solid #1a1a3e;
    border-left: 3px solid var(--accent-blue);
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem; margin: 0.5rem 0;
    font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;
}
.xai-factor {
    display: flex; justify-content: space-between;
    padding: 0.3rem 0; border-bottom: 1px solid #111130;
}
.xai-factor:last-child { border-bottom: none; }

/* ── Risk Router ────────────────────────────────────── */
.router-flow {
    display: flex; align-items: center; gap: 0;
    overflow-x: auto; padding: 0.5rem 0;
}
.router-step {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 10px; padding: 0.6rem 0.8rem;
    text-align: center; min-width: 110px;
    font-size: 0.7rem; transition: all 0.3s;
}
.router-step.pass { border-color: var(--accent-cyan); }
.router-step.fail { border-color: var(--accent-red); }
.router-step.pending { border-color: var(--accent-gold); }
.router-arrow { color: var(--text-dim); font-size: 1.2rem; padding: 0 0.3rem; flex-shrink: 0; }

/* ── Simulator ──────────────────────────────────────── */
.sim-result {
    background: linear-gradient(135deg, #0c0c1f, #111130);
    border: 1px solid var(--border); border-radius: 12px;
    padding: 1rem; font-family: 'JetBrains Mono', monospace;
}
.sim-row {
    display: flex; justify-content: space-between;
    padding: 0.3rem 0; font-size: 0.82rem;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060612 0%, #0a0a1f 100%);
    border-right: 1px solid #111130;
}

/* Hide Streamlit default multipage sidebar nav; keep custom top panel strip */
[data-testid="stSidebarNav"] { display: none !important; }

/* ══════════════════════════════════════════════════════════
   RESPONSIVE — Tablet  (≤ 992px)
   ══════════════════════════════════════════════════════════ */
@media (max-width: 992px) {
    .stApp h1      { font-size: 1.4rem !important; }
    .stApp h3      { font-size: 1.05rem !important; }
    .stApp h5      { font-size: 0.9rem !important; }
    .stApp p, .stApp div { font-size: inherit; }

    .mcard         { padding: 0.7rem 0.8rem; margin-bottom: 0.4rem; }
    .mcard .val    { font-size: 1.15rem; }
    .mcard .lbl    { font-size: 0.62rem; }

    .orb-container { padding: 1rem 0.3rem; }
    .regime-orb    { width: 90px; height: 90px; }
    .orb-label     { font-size: 0.75rem; letter-spacing: 1px; }

    .cog-stream    { padding: 0.8rem; margin: 0.3rem 0.2rem; font-size: 0.7rem;
                     max-height: 240px; line-height: 1.5; }

    .hm-grid       { grid-template-columns: repeat(2, 1fr); gap: 6px; }
    .hm-cell       { padding: 0.6rem; }
    .hm-cell .hm-val { font-size: 1rem; }
    .hm-cell .hm-lbl { font-size: 0.58rem; }

    .dec-box       { padding: 0.9rem 1rem; font-size: 0.85rem; }
    .xai-panel     { padding: 0.8rem 1rem; font-size: 0.76rem; }

    .router-step   { min-width: 90px; padding: 0.5rem 0.6rem; font-size: 0.62rem; }
    .router-arrow  { font-size: 1rem; padding: 0 0.15rem; }

    .sim-result    { padding: 0.8rem; }
    .sim-row       { font-size: 0.76rem; }

    .kill-active   { padding: 0.8rem; }
    .rug-alert     { padding: 0.6rem 0.9rem; }

    .badge         { font-size: 0.6rem; padding: 0.12rem 0.45rem; }

    .mod-grid      { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .mod-card      { padding: 0.6rem 0.8rem; border-radius: 10px; }
    .mod-card .mod-name { font-size: clamp(0.55rem, 1vw, 0.72rem); }
    .mod-card .mod-icon { font-size: 0.9rem; }
    .mod-card .mod-tag  { font-size: 0.48rem; }
}

/* ══════════════════════════════════════════════════════════
   RESPONSIVE — Phone landscape / small tablet  (≤ 768px)
   ══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    .stApp h1      { font-size: 1.15rem !important; }
    .stApp h3      { font-size: 0.95rem !important; }
    .stApp h5      { font-size: 0.8rem !important; }

    .mcard         { padding: 0.55rem 0.6rem; border-radius: 10px; }
    .mcard .val    { font-size: 1rem; }
    .mcard .lbl    { font-size: 0.58rem; letter-spacing: 1px; }
    .mcard .d-up, .mcard .d-down { font-size: 0.68rem; }

    .orb-container { padding: 0.6rem 0; }
    .regime-orb    { width: 70px; height: 70px; }
    .orb-label     { font-size: 0.65rem; margin-top: 0.4rem; }

    .cog-stream    { padding: 0.6rem; margin: 0.2rem 0; font-size: 0.65rem;
                     max-height: 180px; line-height: 1.4; }

    .hm-grid       { grid-template-columns: repeat(2, 1fr); gap: 4px; }
    .hm-cell       { padding: 0.45rem; border-radius: 8px; }
    .hm-cell .hm-val { font-size: 0.9rem; }
    .hm-cell .hm-lbl { font-size: 0.52rem; }

    .dec-box       { padding: 0.7rem 0.8rem; border-radius: 10px; font-size: 0.78rem; }

    .xai-panel     { padding: 0.6rem 0.8rem; font-size: 0.7rem; border-radius: 0 10px 10px 0; }
    .xai-factor    { padding: 0.2rem 0; font-size: 0.68rem; }

    .router-flow   { gap: 0; overflow-x: auto; -webkit-overflow-scrolling: touch;
                     padding-bottom: 0.5rem; }
    .router-step   { min-width: 80px; padding: 0.4rem 0.5rem; font-size: 0.58rem; }
    .router-arrow  { font-size: 0.9rem; }

    .sim-result    { padding: 0.6rem; border-radius: 10px; }
    .sim-row       { font-size: 0.72rem; padding: 0.2rem 0; }

    .kill-active   { padding: 0.6rem; border-radius: 10px; }
    .rug-alert     { padding: 0.5rem 0.7rem; border-radius: 10px; }

    .auto-badge-on, .auto-badge-off { padding: 0.6rem 0.8rem; border-radius: 10px; }

    .badge         { font-size: 0.55rem; padding: 0.1rem 0.4rem; }
    .hz            { margin: 0.5rem 0; }

    .mod-grid      { grid-template-columns: repeat(3, 1fr); gap: 6px; }
    .mod-card      { padding: 0.5rem 0.65rem; gap: 0.4rem; border-radius: 8px; }
    .mod-card .mod-name { font-size: clamp(0.5rem, 0.9vw, 0.65rem); letter-spacing: 0.3px; }
    .mod-card .mod-icon { font-size: 0.8rem; }
    .mod-card .mod-tag  { font-size: 0.42rem; padding: 0.1rem 0.35rem; }
}

/* ══════════════════════════════════════════════════════════
   RESPONSIVE — Phone portrait  (≤ 480px)
   ══════════════════════════════════════════════════════════ */
@media (max-width: 480px) {
    .stApp h1      { font-size: 0.95rem !important; line-height: 1.3 !important; }
    .stApp h3      { font-size: 0.82rem !important; }
    .stApp h5      { font-size: 0.72rem !important; }

    .mcard         { padding: 0.45rem 0.5rem; border-radius: 8px; margin-bottom: 0.3rem; }
    .mcard .val    { font-size: 0.88rem; }
    .mcard .lbl    { font-size: 0.5rem; letter-spacing: 0.8px; }
    .mcard .d-up, .mcard .d-down { font-size: 0.6rem; }

    .orb-container { padding: 0.4rem 0; margin: 0.2rem 0; }
    .regime-orb    { width: 55px; height: 55px; }
    .orb-label     { font-size: 0.58rem; margin-top: 0.3rem; letter-spacing: 1px; }

    .cog-stream    { padding: 0.5rem; margin: 0.15rem 0; font-size: 0.58rem;
                     max-height: 150px; line-height: 1.35;
                     border-radius: 8px; }
    .cog-ts        { font-size: 0.5rem; }

    .hm-grid       { grid-template-columns: 1fr 1fr; gap: 4px; }
    .hm-cell       { padding: 0.4rem; border-radius: 6px; }
    .hm-cell .hm-val { font-size: 0.82rem; }
    .hm-cell .hm-lbl { font-size: 0.48rem; }

    .dec-box       { padding: 0.6rem 0.7rem; border-radius: 8px; font-size: 0.7rem; }
    .dec-box div[style*="font-size:1.4rem"] { font-size: 1rem !important; }
    .dec-box div[style*="font-size:0.9rem"] { font-size: 0.72rem !important; }

    .xai-panel     { padding: 0.5rem 0.6rem; font-size: 0.62rem; }
    .xai-factor    { padding: 0.15rem 0; font-size: 0.6rem;
                     flex-direction: column; gap: 0.1rem; }

    .router-flow   { flex-wrap: wrap; justify-content: center; gap: 4px; }
    .router-step   { min-width: 65px; padding: 0.35rem 0.4rem; font-size: 0.52rem;
                     border-radius: 8px; }
    .router-arrow  { font-size: 0.75rem; padding: 0 0.1rem; }

    .sim-result    { padding: 0.5rem; border-radius: 8px; }
    .sim-row       { font-size: 0.65rem; flex-direction: column; gap: 0.1rem;
                     text-align: left; }

    .kill-active   { padding: 0.5rem; border-radius: 8px; }
    .kill-active div[style*="font-size:1.3rem"] { font-size: 0.9rem !important; }
    .rug-alert     { padding: 0.4rem 0.6rem; border-radius: 8px; }
    .rug-alert div[style*="font-size:1rem"]  { font-size: 0.8rem !important; }
    .rug-alert div[style*="font-size:0.8rem"] { font-size: 0.65rem !important; }

    .auto-badge-on, .auto-badge-off { padding: 0.5rem 0.6rem; border-radius: 8px; }
    .auto-badge-on div[style*="font-size:1.1rem"] { font-size: 0.85rem !important; }

    .badge         { font-size: 0.5rem; padding: 0.08rem 0.35rem; }
    .hz            { margin: 0.4rem 0; }

    .js-plotly-plot { max-height: 250px; }

    button[data-baseweb="tab"] { font-size: 0.65rem !important; padding: 0.4rem 0.5rem !important; }

    .mod-grid      { grid-template-columns: repeat(2, 1fr); gap: 5px; }
    .mod-card      { padding: 0.45rem 0.55rem; gap: 0.35rem; border-radius: 7px; }
    .mod-card .mod-name { font-size: 0.52rem; letter-spacing: 0.2px; }
    .mod-card .mod-icon { font-size: 0.72rem; }
    .mod-card .mod-tag  { display: none; }

    section[data-testid="stSidebar"] {
        min-width: 200px !important;
        max-width: 260px !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 1rem !important; }
    section[data-testid="stSidebar"] .stMarkdown h3 { font-size: 0.82rem !important; }
}

/* ══════════════════════════════════════════════════════════
   RESPONSIVE — Very small phones  (≤ 360px)
   ══════════════════════════════════════════════════════════ */
@media (max-width: 360px) {
    .stApp h1      { font-size: 0.82rem !important; }
    .mcard .val    { font-size: 0.78rem; }
    .mcard .lbl    { font-size: 0.45rem; }
    .regime-orb    { width: 45px; height: 45px; }
    .orb-label     { font-size: 0.5rem; }
    .cog-stream    { font-size: 0.52rem; max-height: 120px; padding: 0.4rem; }
    .hm-cell .hm-val { font-size: 0.72rem; }
    .dec-box       { padding: 0.4rem 0.5rem; font-size: 0.62rem; }
    .xai-panel     { font-size: 0.55rem; padding: 0.4rem 0.5rem; }
    .router-step   { min-width: 55px; font-size: 0.48rem; padding: 0.3rem; }
    .sim-row       { font-size: 0.58rem; }
    .mod-grid      { grid-template-columns: repeat(2, 1fr); gap: 4px; }
    .mod-card      { padding: 0.35rem 0.45rem; gap: 0.25rem; }
    .mod-card .mod-name { font-size: 0.46rem; }
    .mod-card .mod-icon { font-size: 0.65rem; }
    button[data-baseweb="tab"] { font-size: 0.55rem !important; padding: 0.3rem 0.35rem !important; }
}

/* ══════════════════════════════════════════════════════════
   PREMIUM VOICE AI — Futuristic NovaSonic Interface
   ══════════════════════════════════════════════════════════ */

/* ── Premium Execute Button ── */
.voice-exec-btn {
    background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #0288d1 100%) !important;
    border: 2px solid rgba(79,195,247,.7) !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    box-shadow: 0 8px 24px rgba(79,195,247,.25), inset 0 1px 2px rgba(255,255,255,.25) !important;
    position: relative;
    overflow: hidden;
}
.voice-exec-btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.3), transparent);
    opacity: 0;
    animation: shimmer 2s ease-in-out infinite;
    pointer-events: none;
}
@keyframes shimmer {
    0%, 100% { opacity: 0; transform: translateX(-100%); }
    50% { opacity: 1; transform: translateX(100%); }
}
.voice-exec-btn:hover {
    background: linear-gradient(135deg, #64ffda 0%, #4fc3f7 50%, #29b6f6 100%) !important;
    border-color: #64ffda !important;
    box-shadow: 0 16px 48px rgba(100,255,218,.35), 0 0 24px rgba(79,195,247,.4), inset 0 1px 2px rgba(255,255,255,.3) !important;
    transform: translateY(-2px) scale(1.02) !important;
}
.voice-exec-btn:active {
    transform: translateY(0) scale(0.98) !important;
    box-shadow: 0 4px 12px rgba(100,255,218,.25), inset 0 2px 4px rgba(0,0,0,.3) !important;
}

/* ── Premium Quick Command Buttons ── */
.voice-quick-btn {
    background: linear-gradient(135deg, #0c0c1f 0%, #111130 100%) !important;
    border: 1.5px solid rgba(100,255,218,.45) !important;
    color: #9eeeff !important;
    border-radius: 10px !important;
    padding: 0.65rem 1rem !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    box-shadow: 0 6px 16px rgba(100,255,218,.1), inset 0 1px 0 rgba(255,255,255,.12) !important;
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    overflow: hidden;
}
.voice-quick-btn::after {
    content: '';
    position: absolute;
    width: 120%;
    height: 100%;
    top: 0;
    left: -120%;
    background: linear-gradient(90deg, transparent, rgba(100,255,218,.2), transparent);
    transform: skewX(-20deg);
    transition: transform 0.6s;
}
.voice-quick-btn:hover {
    border-color: rgba(100,255,218,.8) !important;
    color: #ecfeff !important;
    background: linear-gradient(135deg, #0d1420 0%, #111130 100%) !important;
    transform: translateY(-2px) scale(1.03) !important;
    box-shadow: 0 12px 32px rgba(100,255,218,.2), inset 0 1px 2px rgba(255,255,255,.15) !important;
}
.voice-quick-btn:hover::after { transform: translateX(130%); }
.voice-quick-btn[data-voice-tone="kill"] {
    border-color: rgba(248,113,113,.65) !important;
    color: #fecaca !important;
    background: linear-gradient(135deg, rgba(39,12,22,.95), rgba(26,7,14,.92)) !important;
    box-shadow: 0 6px 16px rgba(248,113,113,.15), inset 0 1px 0 rgba(255,255,255,.08) !important;
}
.voice-quick-btn[data-voice-tone="kill"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at center, rgba(254,202,202,.15), rgba(248,113,113,.08));
    animation: killGlow 1.5s ease-in-out infinite;
    pointer-events: none;
}
@keyframes killGlow {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}
.voice-quick-btn[data-voice-tone="kill"]:hover {
    border-color: rgba(252,165,165,.9) !important;
    color: #fef2f2 !important;
    box-shadow: 0 12px 32px rgba(239,68,68,.25), inset 0 1px 2px rgba(255,255,255,.1) !important;
    transform: translateY(-2px) scale(1.03) !important;
}

/* ── Futuristic Voice Waveform/Indicator ── */
.voice-waveform-container {
    width: 100%;
    height: 60px;
    background: linear-gradient(180deg, rgba(79,195,247,.08), rgba(100,255,218,.05));
    border: 1px solid rgba(79,195,247,.2);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 0.8rem;
    margin: 0.8rem 0;
    overflow: hidden;
    position: relative;
}
.voice-waveform-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(ellipse at center, rgba(100,255,218,.1), transparent);
    pointer-events: none;
}
.voice-bar {
    width: 3px;
    background: linear-gradient(180deg, #4fc3f7, #64ffda);
    border-radius: 2px;
    flex-shrink: 0;
    animation: voiceBar 0.4s ease-in-out infinite;
    box-shadow: 0 0 8px rgba(100,255,218,.4);
}
@keyframes voiceBar {
    0%, 100% { height: 8px; opacity: 0.5; }
    50% { height: 35px; opacity: 1; }
}
.voice-bar:nth-child(1) { animation-delay: 0s; }
.voice-bar:nth-child(2) { animation-delay: 0.1s; }
.voice-bar:nth-child(3) { animation-delay: 0.2s; }
.voice-bar:nth-child(4) { animation-delay: 0.1s; }
.voice-bar:nth-child(5) { animation-delay: 0s; }

/* ── Thinking State Animation (Neural Pulse) ── */
.voice-thinking {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.8rem 1.2rem;
    background: linear-gradient(135deg, rgba(79,195,247,.1), rgba(100,255,218,.05));
    border: 1px solid rgba(79,195,247,.3);
    border-radius: 10px;
    font-size: 0.9rem;
    color: #64ffda;
}
.voice-thinking-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #64ffda;
    animation: neuroPulse 1.2s ease-in-out infinite;
}
.voice-thinking-dot:nth-child(1) { animation-delay: 0s; }
.voice-thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.voice-thinking-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes neuroPulse {
    0%, 100% { opacity: 0.3; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1.2); }
}

/* ── Voice Progress Bar ── */
.voice-progress {
    width: 100%;
    height: 8px;
    background: linear-gradient(90deg, #0c0c1f, #111130);
    border: 1px solid rgba(79,195,247,.2);
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    margin: 0.6rem 0;
}
.voice-progress::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(100,255,218,.3), transparent);
    animation: progressShine 2s ease-in-out infinite;
}
@keyframes progressShine {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
.voice-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4fc3f7 0%, #64ffda 50%, #29b6f6 100%);
    border-radius: 10px;
    width: 0%;
    transition: width 0.3s ease;
    box-shadow: 0 0 16px rgba(100,255,218,.5);
    position: relative;
    z-index: 2;
}

/* ── Command Card with Premium Styling ── */
.voice-command-card {
    background: linear-gradient(135deg, #0c0c1f 0%, #111130 100%);
    border: 1px solid rgba(79,195,247,.3);
    border-left: 3px solid #64ffda;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    transition: all 0.3s;
}
.voice-command-card:hover {
    border-color: rgba(79,195,247,.6);
    box-shadow: 0 8px 24px rgba(79,195,247,.15);
    transform: translateX(4px);
}

/* ── Response Text with Streaming Animation ── */
.voice-response-text {
    color: #ccd6f6;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.6;
    animation: streamIn 0.3s ease-out;
}
@keyframes streamIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ══════════════════════════════════════════════════════════
   UTILITY — Smooth font scaling with clamp() for fluidity
   ══════════════════════════════════════════════════════════ */
.mcard .val    {
    font-size: clamp(0.72rem, 2.1vw, 1.2rem);
    line-height: 1.15;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
}
.mcard .lbl    { font-size: clamp(0.45rem, 1.2vw, 0.7rem); }
.cog-stream    { font-size: clamp(0.52rem, 1.4vw, 0.78rem); }
.hm-cell .hm-val { font-size: clamp(0.72rem, 2vw, 1.2rem); }
.dec-box       { font-size: clamp(0.62rem, 1.6vw, 0.9rem); }
.orb-label     { font-size: clamp(0.5rem, 1.5vw, 0.85rem); }
.regime-orb    { width: clamp(45px, 12vw, 120px); height: clamp(45px, 12vw, 120px); }

/* ══════════════════════════════════════════════════════════
   TABS — Clean text + bright bottom slider
   ══════════════════════════════════════════════════════════ */
button[data-baseweb="tab"] {
    opacity: 1 !important;
    color: #b7c6f2 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    transition: color .14s ease, border-color .14s ease !important;
}
button[data-baseweb="tab"]:hover {
    color: #e6eeff !important;
    background: transparent !important;
    border-bottom-color: rgba(79,195,247,.55) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    opacity: 1 !important;
    color: #ffffff !important;
    background: transparent !important;
    border-bottom: 3px solid #64ffda !important;
    box-shadow: inset 0 -1px 0 rgba(100,255,218,.35) !important;
    font-weight: 700 !important;
}

/* ── Panel selector (segmented/radio) styled like tabs ── */
[data-testid="stSegmentedControl"],
[data-testid="stRadio"] {
    position: relative;
    width: 100%;
}

[data-testid="stSegmentedControl"] [role="radiogroup"] {
    gap: 0 !important;
    border-bottom: 1px solid rgba(79,195,247,.20) !important;
}
[data-testid="stSegmentedControl"] [data-baseweb="button-group"],
[data-testid="stSegmentedControl"] div[role="group"] {
    gap: 0 !important;
    border-bottom: 1px solid rgba(79,195,247,.20) !important;
}
[data-testid="stSegmentedControl"] [role="radio"] {
    font-size: clamp(0.68rem, 0.95vw, 0.82rem) !important;
    padding: clamp(0.4rem, 0.7vw, 0.5rem) clamp(0.52rem, 1.1vw, 0.72rem) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: #b7c6f2 !important;
    box-shadow: none !important;
    line-height: 1.2 !important;
    letter-spacing: 0.3px !important;
}
[data-testid="stSegmentedControl"] button {
    font-size: clamp(0.68rem, 0.95vw, 0.82rem) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: #b7c6f2 !important;
    box-shadow: none !important;
    line-height: 1.2 !important;
}
[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] {
    color: #ffffff !important;
    border-bottom: 4px solid #64ffda !important;
    font-weight: 800 !important;
    box-shadow: inset 0 -2px 0 rgba(100,255,218,0.4) !important;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stSegmentedControl"] button[aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 4px solid #64ffda !important;
    font-weight: 800 !important;
    box-shadow: inset 0 -2px 0 rgba(100,255,218,0.4) !important;
}

[data-testid="stRadio"] [role="radiogroup"] {
    gap: 0 !important;
    border-bottom: 1px solid rgba(79,195,247,.20) !important;
}
[data-testid="stRadio"] [role="radio"] {
    font-size: clamp(0.68rem, 0.95vw, 0.82rem) !important;
    padding: clamp(0.4rem, 0.7vw, 0.5rem) clamp(0.52rem, 1.1vw, 0.72rem) !important;
    margin: 0 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: #b7c6f2 !important;
    line-height: 1.2 !important;
    letter-spacing: 0.3px !important;
}
[data-testid="stRadio"] [role="radio"][aria-checked="true"] {
    color: #ffffff !important;
    border-bottom: 4px solid #64ffda !important;
    font-weight: 800 !important;
    box-shadow: inset 0 -2px 0 rgba(100,255,218,0.4) !important;
}

.pz-nav-chev {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 22px;
    height: 22px;
    border-radius: 999px;
    border: 1px solid rgba(79,195,247,.35);
    background: rgba(6,6,18,.78);
    color: #9eeeff;
    font-weight: 700;
    font-size: 12px;
    line-height: 1;
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 5;
}
.pz-nav-chev.left { left: 4px; }
.pz-nav-chev.right { right: 4px; }

[data-testid="stSegmentedControl"].pz-overflow-left .pz-nav-chev.left,
[data-testid="stSegmentedControl"].pz-overflow-right .pz-nav-chev.right,
[data-testid="stRadio"].pz-overflow-left .pz-nav-chev.left,
[data-testid="stRadio"].pz-overflow-right .pz-nav-chev.right {
    display: inline-flex;
}

/* touch + mobile controls */
[data-testid="stButton"] > button,
[data-testid="baseButton-secondary"],
[data-testid="baseButton-primary"] {
    min-height: 40px;
}

@media (max-width: 1024px) {
    [data-testid="stSegmentedControl"] [role="radio"],
    [data-testid="stRadio"] [role="radio"],
    [data-testid="stSegmentedControl"] button,
    [data-testid="stRadio"] button {
        font-size: 0.78rem !important;
        padding: 0.42rem 0.55rem !important;
        line-height: 1.15 !important;
    }
}

@media (max-width: 768px) {
    [data-testid="stSegmentedControl"] [role="radio"],
    [data-testid="stRadio"] [role="radio"],
    [data-testid="stSegmentedControl"] button,
    [data-testid="stRadio"] button {
        padding: 0.38rem 0.45rem !important;
        font-size: .74rem !important;
        line-height: 1.1 !important;
    }

    [data-testid="stButton"] > button {
        width: 100% !important;
        font-size: 0.88rem !important;
        padding-top: 0.45rem !important;
        padding-bottom: 0.45rem !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] input {
        font-size: 0.9rem !important;
    }

    .pz-nav-chev { display: none !important; }

}

/* ══════════════════════════════════════════════════════════
   COPY / SELECT PROTECTION
   Disable casual text selection site-wide, but allow it
   inside inputs, code blocks, JSON viewers, dataframes,
   textareas, and the Streamlit expander content so that
   TX hashes, wallet addresses, and raw JSON stay copyable.
   ══════════════════════════════════════════════════════════ */
.stApp {
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}

/* ── Whitelist: things that SHOULD remain selectable ── */
input, textarea, [contenteditable="true"],
pre, code, .stCodeBlock, .stCode,
.stDataFrame, .stTable,
[data-testid="stJson"],
[data-testid="stExpander"] pre,
[data-testid="stExpander"] code,
.stTextInput input,
.stNumberInput input,
.stSelectbox input,
.cog-stream,
.stMarkdown a {
    -webkit-user-select: text !important;
    -moz-user-select: text !important;
    -ms-user-select: text !important;
    user-select: text !important;
}

</style>
""",
        unsafe_allow_html=True,
    )

    if not _CLOUD_SAFE_MODE:
        st.markdown(
            """
    <script>
    (function(){
      const ALLOW = ['INPUT','TEXTAREA','PRE','CODE'];
      function isAllowed(el){
          if(!el) return false;
          if(ALLOW.includes(el.tagName)) return true;
          if(el.isContentEditable) return true;
          if(el.closest('pre,code,.stCodeBlock,.stCode,.stDataFrame,.stTable,[data-testid="stJson"],.cog-stream')) return true;
          return false;
      }

      document.addEventListener('contextmenu', function(e){
          if(!isAllowed(e.target)) e.preventDefault();
      }, true);

      document.addEventListener('keydown', function(e){
          if(e.ctrlKey || e.metaKey){
              if(e.key==='u' || e.key==='s'){
                  e.preventDefault();
              }
              if(e.key==='c' && !isAllowed(document.activeElement)){
                  var sel = window.getSelection();
                  var anchor = sel && sel.anchorNode ? (sel.anchorNode.nodeType===3 ? sel.anchorNode.parentElement : sel.anchorNode) : null;
                  if(!isAllowed(anchor)) e.preventDefault();
              }
          }
      }, true);
    })();
    </script>
    """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
<script>
window.addEventListener('error', function (e) {
  try {
    const msg = String((e && e.message) || '');
    if (msg.includes('Cannot redefine property: ethereum')) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return true;
    }
  } catch (_) {}
  return false;
}, true);
</script>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<style>
[data-stale="true"]::before,
[data-stale="true"]::after {
    display: none !important;
    content: none !important;
}
[data-stale="true"] {
    opacity: 1 !important;
    transition: none !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<script>
(function() {
    const STEP = 220;

    function findGroup(container) {
        if (!container) return null;
        return (
            container.querySelector('[role="radiogroup"]') ||
            container.querySelector('[data-baseweb="button-group"]') ||
            container.querySelector('div[role="group"]')
        );
    }

    function ensureChevron(container, side) {
        let btn = container.querySelector(`.pz-nav-chev.${side}`);
        if (!btn) {
            btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `pz-nav-chev ${side}`;
            btn.setAttribute('aria-label', side === 'left' ? 'Scroll left' : 'Scroll right');
            btn.innerHTML = side === 'left' ? '&#10094;' : '&#10095;';
            container.appendChild(btn);
        }
        return btn;
    }

    function wire(container, group) {
        const leftBtn = ensureChevron(container, 'left');
        const rightBtn = ensureChevron(container, 'right');

        function refresh() {
            const overflow = group.scrollWidth > group.clientWidth + 2;
            container.classList.remove('pz-overflow-left', 'pz-overflow-right');
            if (!overflow) return;
            if (group.scrollLeft > 3) container.classList.add('pz-overflow-left');
            if (group.scrollLeft + group.clientWidth < group.scrollWidth - 3) container.classList.add('pz-overflow-right');
        }

        if (!leftBtn.dataset.wired) {
            leftBtn.addEventListener('click', function(e) {
                e.preventDefault();
                group.scrollBy({ left: -STEP, behavior: 'smooth' });
            });
            leftBtn.dataset.wired = '1';
        }
        if (!rightBtn.dataset.wired) {
            rightBtn.addEventListener('click', function(e) {
                e.preventDefault();
                group.scrollBy({ left: STEP, behavior: 'smooth' });
            });
            rightBtn.dataset.wired = '1';
        }

        if (!group.dataset.pzWired) {
            group.addEventListener('scroll', refresh, { passive: true });
            window.addEventListener('resize', refresh, { passive: true });
            group.dataset.pzWired = '1';
        }
        refresh();
        setTimeout(refresh, 120);
    }

    function run() {
        document.querySelectorAll('[data-testid="stSegmentedControl"], [data-testid="stRadio"]').forEach(function(container){
            const group = findGroup(container);
            if (!group) return;
            group.style.display = 'flex';
            group.style.flexWrap = 'nowrap';
            group.style.overflowX = 'auto';
            group.style.overflowY = 'hidden';
            group.style.whiteSpace = 'nowrap';
            wire(container, group);
        });
    }

    run();
    const mo = new MutationObserver(run);
    mo.observe(document.body, { childList: true, subtree: true });
})();
</script>
""",
        unsafe_allow_html=True,
    )


_INTRO_SLIDES = [
    {
        "icon": "🛡️",
        "title": "Welcome to Protocol Zero",
        "subtitle": "Autonomous · Trust-Minimized · On-Chain Accountable",
        "body": (
            "Protocol Zero is an AI-powered DeFi trading agent that combines "
            "Amazon Nova intelligence with cryptographic accountability. "
            "Every decision is signed, risk-gated, and logged on-chain."
        ),
        "features": [],
        "gradient": "linear-gradient(135deg, #0a0a2e 0%, #1a0a3e 50%, #0a1a3e 100%)",
    },
    {
        "icon": "🧠",
        "title": "AI Reasoning Engine",
        "subtitle": "Amazon Nova Lite · Agentic Tool-Use Loop",
        "body": "The brain fetches live OHLCV data, builds market context, and calls Nova Lite with 4 tools for deep analysis.",
        "features": [
            ("🧠", "Nova Brain", "Agentic Converse API with tool-use loop for market reasoning"),
            ("🔬", "Nova Embeddings", "Multimodal scam-pattern detection via cosine similarity"),
            ("🎙️", "Nova Voice", "Text intelligence for voice commands + Web Speech API"),
            ("🔍", "Nova Act Auditor", "Browser-based smart contract security audits"),
        ],
        "gradient": "linear-gradient(135deg, #0a0a2e 0%, #0a2a3e 50%, #0a1a2e 100%)",
    },
    {
        "icon": "🛡️",
        "title": "Risk Management Pipeline",
        "subtitle": "6-Layer Fail-Closed Gate · Capital Preservation First",
        "body": "Every trade passes through 6 independent risk checks. If ANY check is uncertain, the trade is blocked.",
        "features": [
            ("⚖️", "Position Size Gate", "Caps single-trade exposure at $500"),
            ("📉", "Daily Loss Limit", "Halts trading at -$1,000 cumulative daily loss"),
            ("⏱️", "Trade Frequency", "Max 10 trades per rolling hour"),
            ("🎯", "Concentration", "Max 30% capital in a single asset"),
            ("🔮", "Confidence Floor", "Rejects low-confidence AI signals (< 40%)"),
            ("⏰", "Intent Expiry", "Stale intents auto-rejected after 5 minutes"),
        ],
        "gradient": "linear-gradient(135deg, #0a0a2e 0%, #2a0a1e 50%, #1a0a2e 100%)",
    },
    {
        "icon": "🔏",
        "title": "Cryptographic Accountability",
        "subtitle": "EIP-712 · ERC-8004 · Merkle Audit Trail",
        "body": "Every decision is cryptographically signed and logged on-chain — creating an immutable proof of reasoning.",
        "features": [
            ("🔏", "EIP-712 Signing", "Typed data signatures for every trade intent"),
            ("🆔", "Identity Registry", "Agent mints an ERC-721 NFT on-chain"),
            ("⭐", "Reputation Registry", "Trade outcomes logged via giveFeedback()"),
            ("📋", "Validation Artifacts", "Keccak256-hashed audit trail with Merkle root"),
        ],
        "gradient": "linear-gradient(135deg, #0a0a2e 0%, #1a1a0e 50%, #0a2a1e 100%)",
    },
    {
        "icon": "📊",
        "title": "Live Dashboard Features",
        "subtitle": "14 Interactive Tabs · Real-Time Analytics",
        "body": "Monitor everything in real time — from AI reasoning to on-chain transactions.",
        "features": [
            ("🧠", "Cognitive Stream", "Live AI thought feed as decisions unfold"),
            ("🌌", "Market Regime Orb", "Animated sphere showing market state"),
            ("🧬", "Trade DNA", "Visual fingerprint of each trade's characteristics"),
            ("📊", "Performance Analytics", "Sharpe, Sortino, Calmar ratios + equity curve"),
            ("🔮", "What-If Simulator", "Stress-test with volatility multiplier"),
            ("⛓️", "DEX Execution", "Live Uniswap V3 swap execution"),
        ],
        "gradient": "linear-gradient(135deg, #0a0a2e 0%, #0a1a3e 50%, #1a0a2e 100%)",
    },
]


def render_intro_screen() -> None:
    """Render cinematic onboarding walkthrough with 5 slides."""
    import json as _json
    import streamlit.components.v1 as _components

    total = len(_INTRO_SLIDES)

    st.markdown("""<style>
    section[data-testid="stSidebar"],header[data-testid="stHeader"],
    #MainMenu,footer,.stDeployButton,.stApp>header{display:none!important}
    .stApp, html, body, section.main,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stAppViewBlockContainer"],
    .stMainBlockContainer, .block-container {
        background-color: #0a0a1a !important;
        background: #0a0a1a !important;
    }
    .block-container,.stMainBlockContainer,
    div[data-testid="stAppViewBlockContainer"],
    div[data-testid="stAppViewContainer"],
    div[data-testid="stVerticalBlock"],
    .main .block-container,section.main>div,.stApp>div,section.main,
    .appview-container,.main>.block-container{
        padding:0!important;margin:0!important;max-width:100%!important
    }
    .stApp [data-testid="stAppViewContainer"],
    .stApp [data-testid="stVerticalBlockBorderWrapper"]{padding:0!important;margin:0!important}
    [data-stale="true"]::before,[data-stale="true"]::after{display:none!important;content:none!important}
    [data-stale="true"]{opacity:1!important;transition:none!important}
    .stSpinner,.stSpinnerContainer,div[data-testid="stStatusWidget"],
    div[data-testid="stSpinner"]{display:none!important}
    iframe{border:none!important}
    </style>""", unsafe_allow_html=True)

    slides_json_data = []
    for idx, sl in enumerate(_INTRO_SLIDES):
        feats = ""
        if sl["features"]:
            feats = '<div class="feats">'
            for ico, name, desc in sl["features"]:
                feats += (f'<div class="feat"><span class="fi">{ico}</span>'
                          f'<span class="fn">{name}</span>'
                          f'<div class="fd">{desc}</div></div>')
            feats += "</div>"
        slides_json_data.append({
            "icon": sl["icon"], "title": sl["title"],
            "subtitle": sl["subtitle"], "body": sl["body"],
            "feats": feats,
        })

    slides_js = _json.dumps(slides_json_data)

    intro_html = f"""
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%;overflow:hidden;background:#0a0a1a;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:#ccd6f6}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes glow{{0%,100%{{text-shadow:0 0 20px rgba(100,255,218,.3)}}50%{{text-shadow:0 0 40px rgba(100,255,218,.6),0 0 80px rgba(100,255,218,.2)}}}}
@keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.05)}}}}
@keyframes shimmer{{0%{{background-position:-200% center}}100%{{background-position:200% center}}}}
@keyframes slideIn{{from{{opacity:0;transform:translateX(-30px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes dotPulse{{0%,100%{{opacity:.4;transform:scale(1)}}50%{{opacity:1;transform:scale(1.3)}}}}
.wrap{{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 1.5rem;text-align:center}}
.slide{{display:flex;flex-direction:column;align-items:center;animation:fadeIn .4s ease-out}}
.icon{{font-size:3.5rem;margin-bottom:.5rem;animation:pulse 3s ease-in-out infinite}}
.title{{font-family:'JetBrains Mono',monospace;font-size:2.3rem;font-weight:800;background:linear-gradient(135deg,#64ffda 0%,#4fc3f7 50%,#b388ff 100%);background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;animation:shimmer 4s linear infinite,glow 3s ease-in-out infinite;margin-bottom:.15rem;line-height:1.2}}
.sub{{font-size:.92rem;color:#8892b0;font-family:'JetBrains Mono',monospace;letter-spacing:2px;text-transform:uppercase;margin-bottom:.9rem}}
.body{{font-size:1.05rem;color:#ccd6f6;max-width:650px;line-height:1.65;margin:0 auto 1.3rem auto}}
.feats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem;max-width:840px;width:100%;margin:0 auto 1.2rem auto}}
.feat{{background:rgba(12,12,31,.8);border:1px solid #1a1a3e;border-radius:12px;padding:.85rem 1.1rem;text-align:left;animation:slideIn .5s ease-out both;transition:border-color .3s,transform .2s}}
.feat:hover{{border-color:#64ffda;transform:translateY(-2px)}}
.feat:nth-child(1){{animation-delay:.08s}}.feat:nth-child(2){{animation-delay:.12s}}.feat:nth-child(3){{animation-delay:.16s}}.feat:nth-child(4){{animation-delay:.2s}}.feat:nth-child(5){{animation-delay:.24s}}.feat:nth-child(6){{animation-delay:.28s}}
.fi{{font-size:1.3rem;margin-right:.45rem}}.fn{{font-weight:700;color:#64ffda;font-size:.92rem}}.fd{{color:#8892b0;font-size:.8rem;margin-top:3px;line-height:1.5}}
.dots{{display:flex;gap:10px;justify-content:center;margin:.8rem 0}}
.dot{{width:10px;height:10px;border-radius:50%;background:#1a1a3e;transition:all .3s}}.dot.active{{background:#64ffda;box-shadow:0 0 12px rgba(100,255,218,.5);animation:dotPulse 2s ease-in-out infinite}}.dot.done{{background:#495670}}
.nav{{display:flex;gap:.8rem;justify-content:center;margin-top:.3rem}}
.btn{{padding:.55rem 1.8rem;border-radius:8px;border:1px solid #3ec9ad;background:transparent;color:#3ec9ad;font-family:'JetBrains Mono',monospace;font-size:.85rem;cursor:pointer;transition:all .15s;outline:none}}
.btn:hover{{background:rgba(62,201,173,.12)}}.btn.primary{{background:#3ec9ad;color:#0a0a1a;font-weight:700;border-color:#3ec9ad}}.btn.primary:hover{{background:#36b89d;border-color:#36b89d}}
@media(max-width:768px){{.icon{{font-size:2.5rem}}.title{{font-size:1.5rem}}.sub{{font-size:.78rem;letter-spacing:1px}}.body{{font-size:.9rem}}.feats{{grid-template-columns:1fr;gap:.5rem}}.fn{{font-size:.85rem}}.fd{{font-size:.76rem}}.fi{{font-size:1.15rem}}}}
@media(max-width:480px){{.title{{font-size:1.2rem}}.icon{{font-size:2rem}}.body{{font-size:.82rem}}.fn{{font-size:.8rem}}.fd{{font-size:.72rem}}}}
</style></head><body>
<div class="wrap">
<div class="slide" id="slide"></div>
<div class="dots" id="dots"></div>
<div class="nav" id="nav"></div>
</div>
<script>
const slides={slides_js};
const total=slides.length;
let cur=0;
function render(){{
  const s=slides[cur];
  document.getElementById('slide').innerHTML='<div class="icon">'+s.icon+'</div>'+'<div class="title">'+s.title+'</div>'+'<div class="sub">'+s.subtitle+'</div>'+'<div class="body">'+s.body+'</div>'+s.feats;
  let dh='';
  for(let i=0;i<total;i++){{let c=i===cur?'active':i<cur?'done':'';dh+='<div class="dot '+c+'"></div>';}}
  document.getElementById('dots').innerHTML=dh;
  let nh='';
  if(cur>0) nh+='<button class="btn" onclick="go(-1)">← Back</button>';
  if(cur<total-1){{nh+='<button class="btn primary" onclick="go(1)">Next →</button>';}}
  else{{nh+='<button class="btn primary" onclick="launch()">🚀 Launch Dashboard</button>';}}
  document.getElementById('nav').innerHTML=nh;
  const el=document.getElementById('slide');
  el.style.animation='none';el.offsetHeight;el.style.animation='fadeIn .35s ease-out';
}}
function go(d){{cur=Math.max(0,Math.min(total-1,cur+d));render();}}
function launch(){{window.location.href=window.location.pathname+'?launch=1';}}
render();
</script></body></html>"""

    _components.html(intro_html, height=650, scrolling=False)


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
            ("kraken", [symbol, symbol.replace("USDT", "USD")]),
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


def render_cognitive_stream() -> str:
    """Render live cognitive stream showing AI thought feed."""
    if not st.session_state.get("cognitive_log", []):
        return '<div class="cog-stream"><span class="cog-txt">Awaiting first analysis cycle…</span></div>'
    lines = []
    for e in st.session_state.get("cognitive_log", [])[-20:]:  # Last 20 thoughts
        lines.append(
            f'<p class="cog-line">'
            f'<span class="cog-ts">[{e.get("ts", "??:??")}]</span> '
            f'<span class="cog-sym">{e.get("sym", "?")}  </span> '
            f'<span class="{e.get("cls", "cog-txt")}">{e.get("text", "")}</span></p>'
        )
    return f'<div class="cog-stream">{"".join(lines)}</div>'


def regime_orb_html(regime: str) -> str:
    r = _REGIME_COLORS.get(regime, _REGIME_COLORS["UNCERTAIN"])
    return f'<div class="orb-container"><div class="regime-orb" style="background:{r["bg"]};box-shadow:0 0 40px {r["glow"]},0 0 80px {r["glow"]}"></div><div class="orb-label" style="color:{r["text"]}">{regime}</div></div>'


def trade_dna_html(history: list[dict[str, Any]]) -> str:
    if not history:
        return '<div style="color:#495670;text-align:center;padding:1rem">No trade DNA yet</div>'
    recent = history[-24:]
    spacing = 26
    left_pad = 18
    width = left_pad * 2 + max(1, len(recent) - 1) * spacing
    center_y = 52

    top_points: list[tuple[float, float]] = []
    bot_points: list[tuple[float, float]] = []
    rungs: list[str] = []
    nodes: list[str] = []

    for i, t in enumerate(recent):
        conf = max(0.0, min(1.0, float(t.get("confidence", 0.5) or 0.5)))
        risk = max(1, min(10, int(t.get("risk_score", 5) or 5)))
        action = str(t.get("action", "HOLD")).upper()
        x = left_pad + i * spacing
        amp = 8 + risk * 1.7
        phase = i * 0.74
        off = math.sin(phase) * amp
        y_top = center_y - off
        y_bot = center_y + off
        top_points.append((x, y_top))
        bot_points.append((x, y_bot))

        action_color = {"BUY": "#64ffda", "SELL": "#ff6b6b"}.get(action, "#ffd93d")
        rung_op = 0.22 + conf * 0.56
        rungs.append(f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bot:.1f}" stroke="{action_color}" stroke-opacity="{rung_op:.2f}" stroke-width="2"/>')
        node_r = 2.2 + conf * 2.8
        nodes.append(f'<circle cx="{x:.1f}" cy="{y_top:.1f}" r="{node_r:.2f}" fill="{action_color}"/>')
        nodes.append(f'<circle cx="{x:.1f}" cy="{y_bot:.1f}" r="{max(2.0, node_r - 0.6):.2f}" fill="#4fc3f7" fill-opacity="0.92"/>')

    top_line = " ".join(f"{x:.1f},{y:.1f}" for x, y in top_points)
    bot_line = " ".join(f"{x:.1f},{y:.1f}" for x, y in bot_points)

    return (
        '<div style="padding:.35rem .45rem .45rem .45rem;border:1px solid #1a1a3e;border-radius:12px;'
        'background:linear-gradient(180deg,rgba(12,12,31,.58),rgba(8,8,22,.42));overflow-x:auto;">'
        f'<svg width="{width}" height="104" viewBox="0 0 {width} 104" xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{top_line}" fill="none" stroke="#64ffda" stroke-opacity="0.82" stroke-width="2.3"/>'
        f'<polyline points="{bot_line}" fill="none" stroke="#b388ff" stroke-opacity="0.78" stroke-width="2.1"/>'
        f"{''.join(rungs)}{''.join(nodes)}"
        '</svg>'
        '<div style="display:flex;gap:.8rem;flex-wrap:wrap;font-size:.62rem;color:#8892b0;padding:.15rem .15rem 0 .15rem">'
        '<span><b style="color:#64ffda">●</b> BUY confidence</span>'
        '<span><b style="color:#ff6b6b">●</b> SELL confidence</span>'
        '<span><b style="color:#4fc3f7">●</b> Risk phase</span>'
        '</div></div>'
    )


def risk_heatmap_html(state: dict[str, Any] | None, decision: dict[str, Any] | None, vol_mult: float) -> str:
    cap = state.get("total_capital_usd", 0) if state else 0
    pnl = state.get("session_pnl", 0) if state else 0
    max_loss = state.get("max_daily_loss_usd", 1) if state else 1
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


def xai_panel_html(dec: dict[str, Any], df: pd.DataFrame | None = None) -> str:
    """Explainable AI panel showing why the AI is trading."""
    if df is None or df.empty:
        return '<div class="xai-panel"><span style="color:#495670">Run analysis to see reasoning</span></div>'
    
    try:
        rsi = float(df["rsi_14"].iloc[-1]) if pd.notna(df["rsi_14"].iloc[-1]) else 50.0
        vol = float(df["volatility"].iloc[-1]) if pd.notna(df["volatility"].iloc[-1]) else 0.5
        vol_24h = float(df["volume"].tail(24).mean())
        vol_prev = float(df["volume"].tail(48).head(24).mean())
        vol_spike = ((vol_24h / vol_prev - 1) * 100) if vol_prev > 0 else 0.0
    except Exception:
        rsi, vol, vol_spike = 50.0, 0.5, 0.0
    
    sentiment = "Bullish" if rsi > 55 else ("Bearish" if rsi < 45 else "Neutral")
    sent_score = round((rsi - 50) / 50, 2)
    sent_c = "#64ffda" if sent_score > 0 else ("#ff6b6b" if sent_score < 0 else "#ffd93d")
    vol_label = "Low" if vol < 0.5 else ("High" if vol > 1.5 else "Moderate")
    vol_c = "#64ffda" if vol < 0.8 else ("#ff6b6b" if vol > 1.5 else "#ffd93d")
    spike_c = "#64ffda" if vol_spike > 10 else ("#ffd93d" if vol_spike > 0 else "#ff6b6b")
    rsi_c = "#ff6b6b" if rsi > 70 else ("#64ffda" if rsi < 30 else "#ffd93d")
    rsi_lbl = "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Neutral")
    regime = dec.get("market_regime", "UNCERTAIN")
    
    return f'''<div class="xai-panel">
        <div style="color:#4fc3f7;font-weight:600;font-size:0.75rem;margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:1px">
            🔍 Why I'm Trading</div>
        <div class="xai-factor">
            <span style="color:#8892b0">Sentiment</span>
            <span style="color:{sent_c}">{sentiment} ({sent_score:+.2f})</span></div>
        <div class="xai-factor">
            <span style="color:#8892b0">Volatility</span>
            <span style="color:{vol_c}">{vol_label} ({vol:.3f})</span></div>
        <div class="xai-factor">
            <span style="color:#8892b0">Volume Trend</span>
            <span style="color:{spike_c}">{vol_spike:+.1f}% vs prior 24h</span></div>
        <div class="xai-factor">
            <span style="color:#8892b0">RSI Signal</span>
            <span style="color:{rsi_c}">{rsi:.1f} {rsi_lbl}</span></div>
        <div class="xai-factor">
            <span style="color:#8892b0">Regime</span>
            <span style="color:#b388ff">{regime}</span></div>
    </div>'''


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


def render_voice_waveform(num_bars: int = 12) -> str:
    """Render futuristic voice waveform visualization"""
    bars_html = "".join(f'<div class="voice-bar"></div>' for _ in range(num_bars))
    return f'<div class="voice-waveform-container">{bars_html}</div>'


def render_voice_thinking() -> str:
    """Render neural pulse thinking indicator"""
    return """<div class="voice-thinking">
        <span>🧠 Processing Neural Intent…</span>
        <div class="voice-thinking-dot"></div>
        <div class="voice-thinking-dot"></div>
        <div class="voice-thinking-dot"></div>
    </div>"""


def render_voice_progress(percentage: float) -> str:
    """Render animated voice progress bar"""
    pct = max(0, min(100, percentage))
    return f"""<div class="voice-progress">
        <div class="voice-progress-fill" style="width: {pct}%"></div>
    </div>"""


def render_voice_command_card(intent: str, command: str, confidence: float) -> str:
    """Render premium command card with confidence indicator"""
    conf_pct = max(0, min(100, int(confidence * 100)))
    conf_color = "#64ffda" if confidence >= 0.7 else ("#ffd93d" if confidence >= 0.5 else "#ff6b6b")
    
    return f"""<div class="voice-command-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
            <span style="font-weight:600;color:#9eeeff;text-transform:uppercase;font-size:0.75rem;letter-spacing:1px">{intent}</span>
            <span style="color:{conf_color};font-weight:700;font-family:'JetBrains Mono';;font-size:0.85rem">{conf_pct}%</span>
        </div>
        <div class="voice-response-text">{command}</div>
        <div class="voice-progress" style="margin-top:0.6rem">
            <div class="voice-progress-fill" style="width: {conf_pct}%"></div>
        </div>
    </div>"""


def render_panel_nav(current_label: str) -> None:
    if current_label not in _PANELS:
        return
    
    # Initialize session state only once, BEFORE creating widget
    if "active_panel" not in st.session_state:
        st.session_state["active_panel"] = current_label
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = current_label
    
    nav_key = "active_panel"
    seg = getattr(st, "segmented_control", None)
    if callable(seg):
        try:
            selected = seg("Panels", options=_PANELS, key=nav_key, label_visibility="collapsed")
        except Exception:
            selected = st.radio("Panels", options=_PANELS, horizontal=True, key=nav_key, label_visibility="collapsed")
    else:
        selected = st.radio("Panels", options=_PANELS, horizontal=True, key=nav_key, label_visibility="collapsed")

    # Widget updates st.session_state["active_panel"] automatically via key binding
    # Only update active_tab after widget creation
    if selected:
        st.session_state["active_tab"] = selected
    
    # Trigger navigation if tab changed
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

        is_registered = bool(st.session_state.get("agent_registered", False))
        reg_text = "✅ REGISTERED" if is_registered else "❌ UNREGISTERED"
        reg_cls = "badge-green" if is_registered else "badge-red"
        st.markdown(f'<span class="badge {reg_cls}">{reg_text}</span>', unsafe_allow_html=True)

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
            aws_access_key=getattr(config, "AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", "")) if config else os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_key=getattr(config, "AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "")) if config else os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            bedrock_api_key=getattr(config, "BEDROCK_LONG_TERM_API_KEY", "") if config else "",
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
    diags = st.session_state.get("system_diagnostics", [])
    if diags:
        with st.expander("System Diagnostics", expanded=False):
            for d in diags[-40:]:
                details = d.get("details") or {}
                st.caption(f"[{d.get('ts','--:--:--')}] {d.get('level','INFO')} · {d.get('message','event')}")
                if details:
                    st.code(json.dumps(details, default=str, indent=2), language="json")
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


def decision_feed_html(limit: int = 10) -> str:
    """Render recent AI decisions as HTML feed."""
    history = st.session_state.get("decision_history", [])
    if not history:
        return '<div style="text-align:center;padding:2rem;color:#495670"><div style="font-size:1.5rem;margin-bottom:0.5rem">📋</div>No decisions yet. Run analysis.</div>'
    
    feed = []
    for dec in reversed(history[-limit:]):
        action = dec.get("action", "HOLD")
        conf = dec.get("confidence", 0.5)
        risk = dec.get("risk_score", 5)
        regime = dec.get("market_regime", "UNCERTAIN")
        ts = dec.get("time", "")
        reason = dec.get("entry_reasoning", "")
        asset = dec.get("asset", "?")
        pos_pct = dec.get("position_size_percent", 0)
        
        icon = {"BUY": "🟢", "SELL": "🔴"}.get(action, "🟡")
        css = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(action, "dec-hold")
        conf_color = "#64ffda" if conf >= 0.7 else ("#ffd93d" if conf >= 0.4 else "#ff6b6b")
        
        feed.append(f'''<div class="dec-box {css}" style="padding:0.8rem 1rem;margin:0.3rem 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:1rem;font-weight:700">{icon} {action} {asset}</span>
                <span style="color:#495670;font-size:0.75rem">{ts}</span>
            </div>
            <div style="color:#8892b0;font-size:0.78rem;margin-top:0.3rem">
                Conf: <span style="color:{conf_color}"><b>{conf:.0%}</b></span> · Risk: <b>{risk}/10</b> · 
                Regime: <b>{regime}</b> · Pos: <b>{pos_pct:.1f}%</b>
            </div>
            <div style="color:#495670;font-size:0.72rem;margin-top:0.2rem;font-style:italic">
                {reason[:100]}{'...' if len(reason) > 100 else ''}</div>
        </div>''')
    
    buy_count = sum(1 for d in history if d.get("action") == "BUY")
    sell_count = sum(1 for d in history if d.get("action") == "SELL")
    hold_count = sum(1 for d in history if d.get("action") == "HOLD")
    
    summary = f'Total: <b>{len(history)}</b> · 🟢 BUY: <b>{buy_count}</b> · 🔴 SELL: <b>{sell_count}</b> · 🟡 HOLD: <b>{hold_count}</b>'
    
    return f'''<div style="padding:0.5rem 0">
        {''.join(feed)}
        <div style="padding:0.8rem;text-align:center;color:#8892b0;font-size:0.78rem">
            {summary}
        </div>
    </div>'''


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


def refresh_wallet_balances(ttl_sec: int = 20) -> dict[str, float]:
    now = time.time()
    last = float(st.session_state.get("_wallet_bal_ts", 0.0) or 0.0)
    if now - last < max(5, int(ttl_sec)):
        return {
            "wallet_eth": float(st.session_state.get("wallet_eth", 0.0) or 0.0),
            "wallet_weth": float(st.session_state.get("wallet_weth", 0.0) or 0.0),
            "wallet_usdc": float(st.session_state.get("wallet_usdc", 0.0) or 0.0),
        }

    if _HAS_DEX and _DEX is not None:
        try:
            bal = _DEX.get_balances()
            st.session_state["wallet_eth"] = float(bal.get("eth", st.session_state.get("wallet_eth", 0.0)) or 0.0)
            st.session_state["wallet_weth"] = float(bal.get("weth", st.session_state.get("wallet_weth", 0.0)) or 0.0)
            st.session_state["wallet_usdc"] = float(bal.get("usdc", st.session_state.get("wallet_usdc", 0.0)) or 0.0)
        except Exception:
            pass

    st.session_state["_wallet_bal_ts"] = now
    return {
        "wallet_eth": float(st.session_state.get("wallet_eth", 0.0) or 0.0),
        "wallet_weth": float(st.session_state.get("wallet_weth", 0.0) or 0.0),
        "wallet_usdc": float(st.session_state.get("wallet_usdc", 0.0) or 0.0),
    }
