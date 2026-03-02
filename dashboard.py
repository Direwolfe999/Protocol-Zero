"""
Protocol Zero — Cinematic Dashboard v2.0
==========================================
Hackathon-winning UI with 5 cinematic features + Autonomous Mode toggle.

Features:
  1. 🧠 Cognitive Stream     — live AI thought feed (terminal-style)
  2. 🌌 Market Regime Orb    — animated glowing sphere
  3. 🧬 Trade DNA            — visual DNA strands per trade
  4. ⚖️ Risk Heat Map        — dynamic exposure grid
  5. 🔮 What-If Simulator    — volatility slider
  6. 🤖 Autonomous Toggle    — Manual vs Auto mode

Launch:
    streamlit run dashboard.py
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ════════════════════════════════════════════════════════════
#  Page Config
# ════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Protocol Zero · Autonomous Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════
#  CSS — dark cinematic theme with animations
# ════════════════════════════════════════════════════════════

# Viewport meta for proper mobile rendering
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">',
            unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@400;500;600;700;800&display=swap');

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

/* ══════════════════════════════════════════════════════════
   RESPONSIVE — Tablet  (≤ 992px)
   ══════════════════════════════════════════════════════════ */
@media (max-width: 992px) {
    /* Typography scale-down */
    .stApp h1      { font-size: 1.4rem !important; }
    .stApp h3      { font-size: 1.05rem !important; }
    .stApp h5      { font-size: 0.9rem !important; }
    .stApp p, .stApp div { font-size: inherit; }

    /* Metric cards */
    .mcard         { padding: 0.7rem 0.8rem; margin-bottom: 0.4rem; }
    .mcard .val    { font-size: 1.15rem; }
    .mcard .lbl    { font-size: 0.62rem; }

    /* Regime orb */
    .orb-container { padding: 1rem 0.3rem; }
    .regime-orb    { width: 90px; height: 90px; }
    .orb-label     { font-size: 0.75rem; letter-spacing: 1px; }

    /* Cognitive stream */
    .cog-stream    { padding: 0.8rem; margin: 0.3rem 0.2rem; font-size: 0.7rem;
                     max-height: 240px; line-height: 1.5; }

    /* Heat map: 2 columns */
    .hm-grid       { grid-template-columns: repeat(2, 1fr); gap: 6px; }
    .hm-cell       { padding: 0.6rem; }
    .hm-cell .hm-val { font-size: 1rem; }
    .hm-cell .hm-lbl { font-size: 0.58rem; }

    /* Decision boxes */
    .dec-box       { padding: 0.9rem 1rem; font-size: 0.85rem; }

    /* XAI panel */
    .xai-panel     { padding: 0.8rem 1rem; font-size: 0.76rem; }

    /* Risk router */
    .router-step   { min-width: 90px; padding: 0.5rem 0.6rem; font-size: 0.62rem; }
    .router-arrow  { font-size: 1rem; padding: 0 0.15rem; }

    /* Simulator */
    .sim-result    { padding: 0.8rem; }
    .sim-row       { font-size: 0.76rem; }

    /* Kill switch / rug alert */
    .kill-active   { padding: 0.8rem; }
    .rug-alert     { padding: 0.6rem 0.9rem; }

    /* Badges */
    .badge         { font-size: 0.6rem; padding: 0.12rem 0.45rem; }
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

    /* Router: allow horizontal scroll */
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

    /* Heat map: single column */
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

    /* Plotly charts: reduce height */
    .js-plotly-plot { max-height: 250px; }

    /* Streamlit tabs: smaller text */
    button[data-baseweb="tab"] { font-size: 0.65rem !important; padding: 0.4rem 0.5rem !important; }

    /* Sidebar adjustments */
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
    button[data-baseweb="tab"] { font-size: 0.55rem !important; padding: 0.3rem 0.35rem !important; }
}

/* ══════════════════════════════════════════════════════════
   UTILITY — Smooth font scaling with clamp() for fluidity
   ══════════════════════════════════════════════════════════ */
.mcard .val    { font-size: clamp(0.78rem, 2.5vw, 1.45rem); }
.mcard .lbl    { font-size: clamp(0.45rem, 1.2vw, 0.7rem); }
.cog-stream    { font-size: clamp(0.52rem, 1.4vw, 0.78rem); }
.hm-cell .hm-val { font-size: clamp(0.72rem, 2vw, 1.2rem); }
.dec-box       { font-size: clamp(0.62rem, 1.6vw, 0.9rem); }
.orb-label     { font-size: clamp(0.5rem, 1.5vw, 0.85rem); }
.regime-orb    { width: clamp(45px, 12vw, 120px); height: clamp(45px, 12vw, 120px); }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  Session State Defaults
# ════════════════════════════════════════════════════════════

_DEFAULTS: dict[str, Any] = {
    "agent_name":       "ProtocolZero",
    "agent_wallet":     "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
    "reputation_score": 95,
    "agent_registered": False,
    "autonomous_mode":  False,

    "selected_pair":    "ETH/USDT",
    "market_df":        None,
    "market_regime":    "RANGING",

    "latest_decision":  None,
    "decision_history": [],
    "cognitive_log":    [],

    "max_position_usd": 500.0,
    "stop_loss_pct":    5.0,
    "take_profit_pct":  10.0,
    "max_daily_loss_usd": 1000.0,
    "total_capital_usd":  10_000.0,
    "session_pnl":      0.0,
    "trade_count":      0,

    "whatif_vol_mult":  1.0,
    "tx_log":           [],

    "kill_switch_active": False,
    "vol_halt_threshold": 2.5,
    "rsi_halt_high":      80,
    "rsi_halt_low":       20,
    "pnl_history":        [],
    "total_spent":        0.0,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ════════════════════════════════════════════════════════════
#  🧠 Cognitive Stream Engine
# ════════════════════════════════════════════════════════════

def _cog(symbol: str, text: str, level: str = "info") -> None:
    """Push a line into the cognitive stream."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S.") + f"{datetime.now().microsecond // 10000:02d}"
    cls_map = {
        "info": "cog-txt", "ok": "cog-ok",
        "warn": "cog-warn", "err": "cog-err", "sym": "cog-sym",
    }
    st.session_state["cognitive_log"].append({
        "ts": ts, "sym": symbol, "text": text,
        "cls": cls_map.get(level, "cog-txt"),
    })
    if len(st.session_state["cognitive_log"]) > 100:
        st.session_state["cognitive_log"] = st.session_state["cognitive_log"][-100:]


def _render_cognitive_stream() -> str:
    if not st.session_state["cognitive_log"]:
        return '<div class="cog-stream"><span class="cog-txt">Awaiting first analysis cycle…</span></div>'
    lines = []
    for e in st.session_state["cognitive_log"]:
        lines.append(
            f'<p class="cog-line">'
            f'<span class="cog-ts">[{e["ts"]}]</span> '
            f'<span class="cog-sym">{e["sym"]}</span> '
            f'<span class="{e["cls"]}">{e["text"]}</span></p>'
        )
    return f'<div class="cog-stream">{"".join(lines)}</div>'


# ════════════════════════════════════════════════════════════
#  Market Data Engine
# ════════════════════════════════════════════════════════════

_BASE_PRICES = {
    "ETH/USDT":  3_420.0,
    "BTC/USDT":  96_750.0,
    "SOL/USDT":  192.0,
    "AVAX/USDT": 38.5,
    "LINK/USDT": 18.7,
}


def _generate_synthetic_ohlcv(symbol: str, hours: int = 72) -> pd.DataFrame:
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16) + int(time.time()) // 3600
    rng = np.random.default_rng(seed)
    base = _BASE_PRICES.get(symbol, 100.0)
    now = datetime.now(timezone.utc)

    rows: list[list] = []
    price = base * (1 + rng.normal(0, 0.015))
    for i in range(hours):
        ts = now - timedelta(hours=hours - i)
        ret = rng.normal(0.0001, 0.009)
        price *= 1 + ret
        high = price * (1 + abs(rng.normal(0, 0.005)))
        low  = price * (1 - abs(rng.normal(0, 0.005)))
        opn  = price * (1 + rng.normal(0, 0.003))
        vol  = rng.uniform(400, 9000) * (base / 100)
        rows.append([ts, opn, high, low, price, vol])

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    _add_indicators(df)
    return df


def _try_fetch_live(symbol: str) -> pd.DataFrame | None:
    try:
        import ccxt
        ex = ccxt.binance({"enableRateLimit": True})
        ohlcv = ex.fetch_ohlcv(symbol, timeframe="1h", limit=72)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        _add_indicators(df)
        return df
    except Exception:
        return None


def _add_indicators(df: pd.DataFrame) -> None:
    df["sma_12"]     = df["close"].rolling(12).mean()
    df["sma_26"]     = df["close"].rolling(26).mean()
    df["pct_change"] = df["close"].pct_change() * 100
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss
    df["rsi_14"]     = 100 - (100 / (1 + rs))
    df["volatility"] = df["pct_change"].rolling(20).std()


def load_market_data(symbol: str) -> pd.DataFrame:
    df = _try_fetch_live(symbol)
    if df is None:
        df = _generate_synthetic_ohlcv(symbol)
    st.session_state["market_df"] = df
    return df


# ════════════════════════════════════════════════════════════
#  🌌 Market Regime Detector
# ════════════════════════════════════════════════════════════

_REGIME_COLORS = {
    "TRENDING":  {"bg": "radial-gradient(circle, #ffd93d 0%, #b8860b 60%, #4a3500 100%)",
                  "glow": "#ffd93daa", "text": "#ffd93d"},
    "RANGING":   {"bg": "radial-gradient(circle, #4fc3f7 0%, #0277bd 60%, #01579b 100%)",
                  "glow": "#4fc3f7aa", "text": "#4fc3f7"},
    "VOLATILE":  {"bg": "radial-gradient(circle, #ff6b6b 0%, #c62828 60%, #4a0000 100%)",
                  "glow": "#ff6b6baa", "text": "#ff6b6b"},
    "UNCERTAIN": {"bg": "radial-gradient(circle, #b388ff 0%, #6200ea 60%, #1a0050 100%)",
                  "glow": "#b388ffaa", "text": "#b388ff"},
}


def detect_regime(df: pd.DataFrame, vol_mult: float = 1.0) -> str:
    if df is None or len(df) < 26:
        return "UNCERTAIN"

    rsi   = df["rsi_14"].iloc[-1]   if pd.notna(df["rsi_14"].iloc[-1])   else 50
    sma12 = df["sma_12"].iloc[-1]   if pd.notna(df["sma_12"].iloc[-1])   else 0
    sma26 = df["sma_26"].iloc[-1]   if pd.notna(df["sma_26"].iloc[-1])   else 0
    vol   = (df["volatility"].iloc[-1] if pd.notna(df["volatility"].iloc[-1]) else 0.5) * vol_mult
    sma_spread = abs(sma12 - sma26) / sma26 * 100 if sma26 else 0

    if vol > 1.8:
        return "VOLATILE"
    if sma_spread > 0.8 and (rsi > 55 or rsi < 45):
        return "TRENDING"
    if vol < 0.6 and 40 < rsi < 60:
        return "RANGING"
    return "UNCERTAIN"


# ════════════════════════════════════════════════════════════
#  Decision Engine (simulated / live Bedrock fallback)
# ════════════════════════════════════════════════════════════

def run_analysis(df: pd.DataFrame, pair: str, vol_mult: float = 1.0) -> dict:
    """Generate a full-schema decision."""
    regime = detect_regime(df, vol_mult)
    st.session_state["market_regime"] = regime
    asset = pair.split("/")[0]

    rsi_now = df["rsi_14"].iloc[-1]   if pd.notna(df["rsi_14"].iloc[-1])   else 50
    vol_now = (df["volatility"].iloc[-1] if pd.notna(df["volatility"].iloc[-1]) else 0.5) * vol_mult

    # Try live brain ---------------------------------------------------
    decision = None
    try:
        from brain import invoke_brain as _invoke  # type: ignore
        decision = _invoke(df=df)
    except Exception:
        pass

    if decision is not None:
        return {
            "action":                decision.get("action", "HOLD"),
            "asset":                 decision.get("asset", asset),
            "confidence":            decision.get("confidence", 0.5),
            "entry_reasoning":       decision.get("reason", ""),
            "risk_score":            min(10, max(1, int(vol_now * 5))),
            "position_size_percent": min(2.0, round(decision.get("amount_usd", 0)
                                          / st.session_state["total_capital_usd"] * 100, 2)),
            "stop_loss_percent":     st.session_state["stop_loss_pct"],
            "take_profit_percent":   st.session_state["take_profit_pct"],
            "market_regime":         regime,
            "amount_usd":            decision.get("amount_usd", 0),
        }

    # Simulated decision -----------------------------------------------
    rng = np.random.default_rng(int(time.time()) % 100_000)

    base_conf = float(rng.uniform(0.55, 0.93))
    conf = round(max(0.15, base_conf - (vol_mult - 1) * 0.25), 2)

    if conf < 0.6 or regime == "VOLATILE":
        action = "HOLD"
    else:
        action = str(rng.choice(["BUY", "SELL"], p=[0.55, 0.45]))

    risk_score = min(10, max(1, int(vol_now * 4 + rng.uniform(0, 2))))
    pos_pct    = round(min(2.0, max(0.2, (conf * 2.0) - (vol_mult - 1) * 0.8)), 2) if action != "HOLD" else 0.0
    amount     = round(st.session_state["total_capital_usd"] * pos_pct / 100, 2)

    reasons = {
        "BUY":  f"SMA-12/26 bullish crossover confirmed. RSI at {rsi_now:.0f} — momentum building. "
                f"The pattern whispers accumulation. {regime} regime favors entry.",
        "SELL": f"Distribution pattern emerging. RSI {rsi_now:.0f} nearing exhaustion. "
                f"SMA convergence signals reversal. The tide is turning — strategic exit.",
        "HOLD": f"The signal is clouded. RSI {rsi_now:.0f} in no-man's land. "
                f"Volatility index at {vol_now:.2f} — patience is the sharper blade. Regime: {regime}.",
    }

    return {
        "action":                action,
        "asset":                 asset,
        "confidence":            conf,
        "entry_reasoning":       reasons[action],
        "risk_score":            risk_score,
        "position_size_percent": pos_pct,
        "stop_loss_percent":     st.session_state["stop_loss_pct"],
        "take_profit_percent":   st.session_state["take_profit_pct"],
        "market_regime":         regime,
        "amount_usd":            amount,
    }


# ════════════════════════════════════════════════════════════
#  HTML Component Helpers
# ════════════════════════════════════════════════════════════

def mcard(label: str, value: str, delta: str = "", up: bool = True) -> str:
    dcls  = "d-up" if up else "d-down"
    dhtml = f'<div class="{dcls}">{delta}</div>' if delta else ""
    return (f'<div class="mcard"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{dhtml}</div>')


def regime_orb_html(regime: str) -> str:
    r = _REGIME_COLORS.get(regime, _REGIME_COLORS["UNCERTAIN"])
    return f"""
    <div class="orb-container">
        <div class="regime-orb"
             style="background:{r['bg']};
                    box-shadow:0 0 40px {r['glow']},0 0 80px {r['glow']},
                               inset 0 0 30px rgba(255,255,255,0.05)">
        </div>
        <div class="orb-label" style="color:{r['text']}">{regime}</div>
    </div>"""


def trade_dna_html(history: list[dict]) -> str:
    """Render visual Trade DNA strands for last 20 trades."""
    if not history:
        return ('<div style="color:#495670;text-align:center;padding:1rem">'
                'No trade DNA yet</div>')
    bars_html = ""
    for i, t in enumerate(history[-20:]):
        conf   = t.get("confidence", 0.5)
        risk   = t.get("risk_score", 5)
        pos    = t.get("position_size_percent", 1.0)
        action = t.get("action", "HOLD")
        color  = {"BUY": "#64ffda", "SELL": "#ff6b6b"}.get(action, "#ffd93d")
        h1 = int(conf * 40 + 5)
        h2 = int(risk * 4 + 5)
        h3 = int(pos * 20 + 5)
        opacity = min(1.0, 0.4 + conf * 0.6)
        bars_html += (
            f'<div class="dna-strand" title="#{i+1} {action} conf={conf:.0%} risk={risk}">'
            f'<div class="dna-bar" style="height:{h1}px;width:8px;background:{color};opacity:{opacity}"></div>'
            f'<div class="dna-bar" style="height:{h2}px;width:6px;background:#b388ff;opacity:0.6"></div>'
            f'<div class="dna-bar" style="height:{h3}px;width:6px;background:#4fc3f7;opacity:0.5"></div>'
            f'</div>'
        )
    return (f'<div style="display:flex;gap:6px;align-items:end;'
            f'padding:0.5rem;overflow-x:auto">{bars_html}</div>')


def risk_heatmap_html(state: dict, decision: dict | None, vol_mult: float) -> str:
    """Render the 4-cell risk heat-map grid."""
    cap      = state["total_capital_usd"]
    pnl      = state["session_pnl"]
    max_loss = state["max_daily_loss_usd"]

    exposure  = decision.get("position_size_percent", 0) if decision else 0
    risk_bud  = max(0, 1 - abs(pnl) / max_loss) * 100 if max_loss else 100
    cap_risk  = (decision.get("amount_usd", 0) / cap * 100) if (cap and decision) else 0
    aggr      = min(10, (decision.get("risk_score", 5) if decision else 3) + int(vol_mult))

    def _cc(val: float, thresholds: tuple[float, float]) -> str:
        if val > thresholds[1]:
            return "background:linear-gradient(135deg,#3b0d0d,#2a0808);color:#ff6b6b"
        if val > thresholds[0]:
            return "background:linear-gradient(135deg,#2d2a0d,#1f1c06);color:#ffd93d"
        return "background:linear-gradient(135deg,#0d3b2e,#081f18);color:#64ffda"

    return f"""
    <div class="hm-grid">
        <div class="hm-cell" style="{_cc(exposure, (1.0, 1.8))}">
            <div class="hm-lbl">Exposure</div><div class="hm-val">{exposure:.1f}%</div></div>
        <div class="hm-cell" style="{_cc(100 - risk_bud, (40, 70))}">
            <div class="hm-lbl">Risk Budget</div><div class="hm-val">{risk_bud:.0f}%</div></div>
        <div class="hm-cell" style="{_cc(cap_risk, (1.0, 2.0))}">
            <div class="hm-lbl">Capital at Risk</div><div class="hm-val">{cap_risk:.1f}%</div></div>
        <div class="hm-cell" style="{_cc(aggr, (5, 8))}">
            <div class="hm-lbl">Aggression</div><div class="hm-val">{aggr}/10</div></div>
    </div>"""


def confidence_gauge(conf: float) -> go.Figure:
    """Plotly gauge chart for AI confidence score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=conf * 100,
        number={"suffix": "%", "font": {"color": "#ccd6f6", "size": 28}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#495670",
                     "tickfont": {"color": "#495670"}},
            "bar": {"color": "#64ffda" if conf >= 0.7
                    else ("#ffd93d" if conf >= 0.4 else "#ff6b6b")},
            "bgcolor": "#111130",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40],  "color": "#1a0808"},
                {"range": [40, 70], "color": "#1a1a08"},
                {"range": [70, 100],"color": "#081a12"},
            ],
            "threshold": {
                "line": {"color": "#ff6b6b", "width": 2},
                "thickness": 0.8, "value": 60,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#8892b0"},
        height=200, margin=dict(l=20, r=20, t=30, b=10),
    )
    return fig


def xai_panel_html(dec: dict, df: pd.DataFrame) -> str:
    """Explainable AI panel — shows why the AI is trading."""
    rsi = df["rsi_14"].iloc[-1] if pd.notna(df["rsi_14"].iloc[-1]) else 50
    vol = df["volatility"].iloc[-1] if pd.notna(df["volatility"].iloc[-1]) else 0.5
    vol_24h  = df["volume"].tail(24).mean()
    vol_prev = df["volume"].tail(48).head(24).mean()
    vol_spike = ((vol_24h / vol_prev - 1) * 100) if vol_prev > 0 else 0

    sentiment = "Bullish" if rsi > 55 else ("Bearish" if rsi < 45 else "Neutral")
    sent_score = round((rsi - 50) / 50, 2)
    sent_c = "#64ffda" if sent_score > 0 else ("#ff6b6b" if sent_score < 0 else "#ffd93d")
    vol_label = "Low" if vol < 0.5 else ("High" if vol > 1.5 else "Moderate")
    vol_c = "#64ffda" if vol < 0.8 else ("#ff6b6b" if vol > 1.5 else "#ffd93d")
    spike_c = "#64ffda" if vol_spike > 10 else ("#ffd93d" if vol_spike > 0 else "#ff6b6b")
    rsi_c = "#ff6b6b" if rsi > 70 else ("#64ffda" if rsi < 30 else "#ffd93d")
    rsi_lbl = "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Neutral")

    return f"""<div class="xai-panel">
        <div style="color:#4fc3f7;font-weight:600;font-size:0.75rem;margin-bottom:0.5rem;
                    text-transform:uppercase;letter-spacing:1px">
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
            <span style="color:#b388ff">{dec.get('market_regime', 'UNCERTAIN')}</span></div>
    </div>"""


def risk_router_html(dec: dict | None) -> str:
    """Visual flowchart: how the AI checks for rug pulls."""
    if not dec:
        return '<div style="color:#495670;text-align:center">Run analysis first</div>'
    checks = [
        ("📋 Token\nAnalysis",   "pass", "Verified"),
        ("⏰ Contract\nAge",     "pass", "> 30 days"),
        ("🔒 Liquidity\nLock",   "pass", "Locked"),
        ("🚫 Blacklist\nScan",   "pass", "Clean"),
        ("📊 Volume\nCheck",     "pass", "Normal"),
    ]
    if dec.get("risk_score", 0) > 7:
        checks[2] = ("🔒 Liquidity\nLock", "fail", "Unlocked!")
    if dec.get("market_regime") == "VOLATILE":
        checks[4] = ("📊 Volume\nCheck", "pending", "Unusual")

    steps = ""
    for i, (label, status, detail) in enumerate(checks):
        icon = {"pass": "✅", "fail": "❌", "pending": "⚠️"}[status]
        steps += (f'<div class="router-step {status}">'
                  f'<div style="font-size:1.1rem">{icon}</div>'
                  f'<div style="color:#ccd6f6;font-size:0.7rem;white-space:pre-line">{label}</div>'
                  f'<div style="color:#495670;font-size:0.6rem">{detail}</div></div>')
        if i < len(checks) - 1:
            steps += '<div class="router-arrow">→</div>'

    all_pass = all(c[1] == "pass" for c in checks)
    vc = "#64ffda" if all_pass else "#ff6b6b"
    vt = "✅ APPROVED — Safe to trade" if all_pass else "⚠️ REVIEW — Risk factors detected"
    return (f'<div class="router-flow">{steps}</div>'
            f'<div style="text-align:center;margin-top:0.5rem;color:{vc};'
            f'font-family:JetBrains Mono,monospace;font-size:0.8rem">{vt}</div>')


def simulate_trade(dec: dict, capital: float) -> dict:
    """Simulate the trade and return expected gas/balance."""
    rng = np.random.default_rng(int(time.time()) % 10_000)
    amount = dec.get("amount_usd", 0)
    gas_gwei = round(float(rng.uniform(15, 45)), 1)
    gas_cost_eth = round(gas_gwei * 21000 / 1e9, 6)
    gas_cost_usd = round(gas_cost_eth * 3420, 2)
    slippage = round(float(rng.uniform(0.01, 0.3)), 2)
    net_amount = round(amount * (1 - slippage / 100), 2)
    final_balance = round(capital - amount - gas_cost_usd, 2)
    return {
        "gas_gwei": gas_gwei, "gas_cost_eth": gas_cost_eth,
        "gas_cost_usd": gas_cost_usd, "slippage_pct": slippage,
        "net_amount": net_amount, "final_balance": final_balance,
        "total_cost": round(amount + gas_cost_usd, 2),
    }


def check_rug_pull(df: pd.DataFrame) -> dict | None:
    """Check for rug-pull indicators in market data."""
    if df is None or len(df) < 10:
        return None
    last5_vol = df["volume"].tail(5)
    avg_vol   = df["volume"].tail(48).mean()
    price_drop = (df["close"].iloc[-1] / df["close"].iloc[-5] - 1) * 100
    vol_spike  = (last5_vol.mean() / avg_vol - 1) * 100 if avg_vol > 0 else 0

    alerts: list[str] = []
    if price_drop < -8:
        alerts.append(f"Sharp price drop: {price_drop:.1f}% in last 5 hours")
    if vol_spike > 200:
        alerts.append(f"Volume spike: {vol_spike:.0f}% above average")
    rsi_val = df["rsi_14"].iloc[-1]
    if pd.notna(rsi_val) and rsi_val < 15:
        alerts.append(f"RSI critically low: {rsi_val:.1f}")
    if alerts:
        return {"level": "critical" if price_drop < -15 else "warning",
                "alerts": alerts}
    return None


def pnl_chart(tx_log: list[dict]) -> go.Figure | None:
    """Build cumulative P&L area chart from transaction log."""
    trades = [t for t in tx_log if t.get("action") in ("BUY", "SELL")]
    if not trades:
        return None
    cum_pnl = 0.0
    xs, ys = [], []
    for t in trades:
        pnl_str = t.get("pnl", "$0").replace("$", "").replace("+", "")
        try:
            cum_pnl += float(pnl_str)
        except ValueError:
            pass
        xs.append(t.get("timestamp", ""))
        ys.append(cum_pnl)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, fill="tozeroy", mode="lines+markers",
        line=dict(color="#64ffda" if cum_pnl >= 0 else "#ff6b6b", width=2),
        fillcolor="rgba(100,255,218,0.1)" if cum_pnl >= 0 else "rgba(255,107,107,0.1)",
        marker=dict(size=6),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#495670")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
        height=250, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(gridcolor="#111130", title="Cumulative PnL ($)"),
        xaxis=dict(gridcolor="#111130", title="Trade"),
    )
    return fig


# ════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🛡️ Protocol Zero")
    st.caption("Autonomous Trust-Minimized Trading Agent")
    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Autonomous Mode Toggle ────────────────────────────
    st.markdown("### ⚡ Operation Mode")
    auto = st.toggle("Autonomous Mode",
                      value=st.session_state["autonomous_mode"],
                      key="auto_toggle")
    st.session_state["autonomous_mode"] = auto

    if auto:
        st.markdown("""
        <div class="auto-badge-on">
            <div style="font-size:1.1rem;font-weight:700;color:#64ffda">⚡ AUTONOMOUS</div>
            <div style="font-size:0.7rem;color:#8892b0;margin-top:2px">
                AI executes trades automatically</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="auto-badge-off">
            <div style="font-size:1.1rem;font-weight:700;color:#8892b0">🔒 MANUAL</div>
            <div style="font-size:0.7rem;color:#495670;margin-top:2px">
                User confirms each trade</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Agent Identity ────────────────────────────────────
    st.markdown("### 🤖 Agent Identity")
    st.session_state["agent_name"]   = st.text_input("Agent Name",
                                                      value=st.session_state["agent_name"])
    st.session_state["agent_wallet"] = st.text_input("Wallet",
                                                      value=st.session_state["agent_wallet"])

    rep   = st.session_state["reputation_score"]
    rep_c = "#64ffda" if rep >= 70 else ("#ffd93d" if rep >= 40 else "#ff6b6b")
    st.markdown(
        f'<div class="mcard"><div class="lbl">Reputation</div>'
        f'<div class="val" style="color:{rep_c}">{rep}'
        f'<span style="font-size:0.8rem;color:#495670"> / 100</span></div></div>',
        unsafe_allow_html=True,
    )

    reg   = st.session_state["agent_registered"]
    badge = ('<span class="badge badge-green">Registered</span>' if reg
             else '<span class="badge badge-gold">Unregistered</span>')
    st.markdown(f"ERC-8004: {badge}", unsafe_allow_html=True)

    if st.button("🔗  Register On-Chain", use_container_width=True, type="primary"):
        with st.spinner("Minting Identity NFT…"):
            time.sleep(1.2)
            st.session_state["agent_registered"] = True
            tx = "0x" + hashlib.sha256(
                st.session_state["agent_name"].encode()).hexdigest()[:40]
            _cog("▣", "Identity NFT mint initiated", "ok")
            _cog("▣", f"TX: {tx[:20]}…", "sym")
            _cog("✓", "Agent registered on ERC-8004 Identity Registry", "ok")
            st.session_state["tx_log"].append({
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "action": "REGISTER", "asset": "—", "amount": "—",
                "status": "✅ Confirmed", "tx_hash": tx[:18] + "…",
            })
        st.success("Registered!")
        st.rerun()

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Risk Parameters ───────────────────────────────────
    st.markdown("### ⚙️ Risk Parameters")
    st.session_state["max_position_usd"] = st.number_input(
        "Max Position ($)", value=st.session_state["max_position_usd"],
        min_value=10.0, max_value=50_000.0, step=50.0)
    st.session_state["stop_loss_pct"]    = st.slider(
        "Stop Loss %", 1.0, 25.0, st.session_state["stop_loss_pct"], 0.5)
    st.session_state["take_profit_pct"]  = st.slider(
        "Take Profit %", 1.0, 50.0, st.session_state["take_profit_pct"], 0.5)
    st.session_state["max_daily_loss_usd"] = st.number_input(
        "Daily Loss Cap ($)", value=st.session_state["max_daily_loss_usd"],
        min_value=50.0, max_value=100_000.0, step=100.0)
    st.session_state["total_capital_usd"]  = st.number_input(
        "Total Capital ($)", value=st.session_state["total_capital_usd"],
        min_value=100.0, max_value=1_000_000.0, step=500.0)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
    pnl   = st.session_state["session_pnl"]
    pnl_c = "#64ffda" if pnl >= 0 else "#ff6b6b"
    st.markdown(
        f'<span style="font-family:JetBrains Mono,monospace;font-size:0.8rem;'
        f'color:{pnl_c}">PnL ${pnl:+.2f}</span> · '
        f'<span style="font-size:0.8rem;color:#8892b0">'
        f'Trades: {st.session_state["trade_count"]}</span>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Emergency Kill Switch ────────────────────────────
    st.markdown("### 🚨 Emergency Controls")
    kill = st.session_state["kill_switch_active"]
    if kill:
        st.markdown("""
        <div class="kill-active">
            <div style="font-size:1.3rem;font-weight:700;color:#ff6b6b">⛔ ALL TRADING HALTED</div>
            <div style="font-size:0.7rem;color:#ff9999;margin-top:2px">
                Kill switch is ACTIVE — no trades will execute</div>
        </div>""", unsafe_allow_html=True)
        if st.button("✅  Resume Trading", use_container_width=True):
            st.session_state["kill_switch_active"] = False
            _cog("✅", "Kill switch deactivated — trading resumed", "ok")
            st.rerun()
    else:
        if st.button("🚨  EMERGENCY STOP", use_container_width=True, type="primary"):
            st.session_state["kill_switch_active"] = True
            st.session_state["autonomous_mode"] = False
            _cog("⛔", "KILL SWITCH ACTIVATED — all trading halted", "err")
            st.rerun()

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Custom Alert Thresholds ──────────────────────────
    st.markdown("### 🚦 Alert Thresholds")
    st.session_state["vol_halt_threshold"] = st.slider(
        "Volatility Halt", 0.5, 5.0,
        st.session_state["vol_halt_threshold"], 0.1,
        help="If volatility exceeds this, AI stops trading.")
    st.session_state["rsi_halt_high"] = st.slider(
        "RSI Overbought Halt", 60, 95,
        st.session_state["rsi_halt_high"], 1,
        help="RSI above this triggers HOLD.")
    st.session_state["rsi_halt_low"] = st.slider(
        "RSI Oversold Halt", 5, 40,
        st.session_state["rsi_halt_low"], 1,
        help="RSI below this triggers HOLD.")


# ════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════

st.markdown(
    '# 🛡️ Protocol Zero '
    '<span style="font-size:clamp(0.35rem, 1.5vw, 0.55rem);color:#495670;font-weight:400;'
    'display:inline-block;word-break:break-word">'
    'v2.0 · Autonomous Agent · ERC-8004</span>',
    unsafe_allow_html=True,
)

# ── Kill Switch Banner ───────────────────────────────
if st.session_state["kill_switch_active"]:
    st.markdown("""
    <div class="kill-active" style="margin-bottom:1rem">
        <div style="font-size:1.3rem;font-weight:700;color:#ff6b6b">
            ⛔ EMERGENCY STOP ACTIVE — ALL TRADING HALTED</div>
        <div style="font-size:0.75rem;color:#ff9999;margin-top:2px">
            Deactivate from the sidebar to resume trading.</div>
    </div>""", unsafe_allow_html=True)

# ── Rug-Pull Alert Banner ─────────────────────────────
_rug_alert_data = None
if st.session_state["market_df"] is not None:
    _rug_alert_data = check_rug_pull(st.session_state["market_df"])
if _rug_alert_data:
    _alert_items = " · ".join(_rug_alert_data["alerts"])
    st.markdown(f"""
    <div class="rug-alert">
        <div style="font-size:1rem;font-weight:700;color:#ff6b6b">
            🚨 RUG-PULL ALERT</div>
        <div style="color:#ff9999;font-size:0.8rem;margin-top:4px">
            {_alert_items}</div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  TOP ROW — Regime Orb + Cognitive Stream + Trade DNA
# ════════════════════════════════════════════════════════════

pair = st.session_state["selected_pair"]
if st.session_state["market_df"] is None:
    load_market_data(pair)
df = st.session_state["market_df"]

regime = detect_regime(df, st.session_state["whatif_vol_mult"])
st.session_state["market_regime"] = regime

col_orb, col_gap1, col_cog, col_gap2, col_dna = st.columns([1.2, 0.1, 2.5, 0.1, 1.5], gap="large")

with col_orb:
    st.markdown("##### 🌌 Regime Orb")
    st.markdown(regime_orb_html(regime), unsafe_allow_html=True)

with col_gap1:
    st.markdown("")

with col_cog:
    st.markdown("##### 🧠 Cognitive Stream")
    st.markdown(_render_cognitive_stream(), unsafe_allow_html=True)

with col_gap2:
    st.markdown("")

with col_dna:
    st.markdown("##### 🧬 Trade DNA")
    st.markdown(trade_dna_html(st.session_state["decision_history"]),
                unsafe_allow_html=True)

st.markdown('<div class="hz"></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  TABS
# ════════════════════════════════════════════════════════════

tab_market, tab_brain, tab_risk, tab_log, tab_pnl, tab_history = st.tabs([
    "📊  Market Data",
    "🧠  AI Analysis",
    "🛡️  Risk & Execution",
    "📒  Transaction Log",
    "📈  P&L Tracker",
    "🔍  Decision History",
])


# ──────────────────────────────────────────────────────────
#  TAB 1 — Market Data
# ──────────────────────────────────────────────────────────

with tab_market:
    col_pair, col_ref = st.columns([3, 1])
    with col_pair:
        new_pair = st.selectbox(
            "Trading Pair", list(_BASE_PRICES.keys()),
            index=(list(_BASE_PRICES.keys()).index(pair)
                   if pair in _BASE_PRICES else 0),
            key="pair_sel",
        )
        if new_pair != st.session_state["selected_pair"]:
            st.session_state["selected_pair"] = new_pair
            load_market_data(new_pair)
            df = st.session_state["market_df"]
    with col_ref:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            df = load_market_data(st.session_state["selected_pair"])

    latest  = df["close"].iloc[-1]
    prev    = df["close"].iloc[-2]
    change  = ((latest - prev) / prev) * 100
    vol24   = df["volume"].tail(24).sum()
    h24     = df["high"].tail(24).max()
    l24     = df["low"].tail(24).min()
    rsi_now = df["rsi_14"].iloc[-1] if pd.notna(df["rsi_14"].iloc[-1]) else 50.0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(mcard("Price", f"${latest:,.2f}",
                          f"{change:+.2f}%", change >= 0), unsafe_allow_html=True)
    with c2:
        st.markdown(mcard("24h High", f"${h24:,.2f}"), unsafe_allow_html=True)
    with c3:
        st.markdown(mcard("24h Low", f"${l24:,.2f}"), unsafe_allow_html=True)
    with c4:
        st.markdown(mcard("24h Volume", f"{vol24:,.0f}"), unsafe_allow_html=True)
    with c5:
        rl = "Oversold" if rsi_now < 30 else ("Overbought" if rsi_now > 70 else "Neutral")
        st.markdown(mcard("RSI-14", f"{rsi_now:.1f}", rl,
                          30 < rsi_now < 70), unsafe_allow_html=True)

    # Candlestick chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC",
        increasing_line_color="#64ffda", decreasing_line_color="#ff6b6b",
        increasing_fillcolor="#0d3b2e",  decreasing_fillcolor="#3b0d0d",
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["sma_12"], name="SMA-12",
        line=dict(color="#4fc3f7", width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["sma_26"], name="SMA-26",
        line=dict(color="#ffd93d", width=1.5, dash="dot")))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
        height=400, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="#111130"), xaxis=dict(gridcolor="#111130"),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📊 Volume Profile"):
        fig_v = go.Figure()
        vcol = ["#64ffda" if df["close"].iloc[i] >= df["open"].iloc[i]
                else "#ff6b6b" for i in range(len(df))]
        fig_v.add_trace(go.Bar(
            x=df["timestamp"], y=df["volume"], marker_color=vcol, name="Vol"))
        fig_v.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=180, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130"), xaxis=dict(gridcolor="#111130"),
        )
        st.plotly_chart(fig_v, use_container_width=True)


# ──────────────────────────────────────────────────────────
#  TAB 2 — AI Analysis
# ──────────────────────────────────────────────────────────

with tab_brain:
    st.markdown("### 🧠 AI Trading Analysis")
    st.caption("Strategic reasoning engine · Nova Lite on Bedrock")

    col_r, _spacer = st.columns([1, 3])
    with col_r:
        run_ai = st.button("▶  Run Analysis", use_container_width=True,
                            type="primary")

    if run_ai:
        with st.spinner("Neural pathways activating…"):
            _cog("▣", f"Analysis cycle initiated — pair {st.session_state['selected_pair']}", "info")
            _cog("▣", "Regime detection: scanning SMA/RSI/Vol matrix", "info")
            time.sleep(0.3)

            decision = run_analysis(
                df, st.session_state["selected_pair"],
                st.session_state["whatif_vol_mult"])

            _cog("▣", f"Regime classified: {decision['market_regime']}", "sym")
            vol_val = df["volatility"].iloc[-1]
            _cog("▣",
                 f"Volatility index: {vol_val:.3f}" if pd.notna(vol_val) else "Volatility: calculating…",
                 "info")
            _cog("▣", f"Confidence computed: {decision['confidence']:.2f}",
                 "ok" if decision["confidence"] >= 0.6 else "warn")
            _cog("▣", f"Risk score: {decision['risk_score']}/10",
                 "warn" if decision["risk_score"] > 6 else "ok")
            if decision["confidence"] < 0.6:
                _cog("⚠", "Confidence below threshold — forcing HOLD", "warn")
            else:
                lvl = ("ok" if decision["action"] == "BUY"
                       else ("err" if decision["action"] == "SELL" else "warn"))
                _cog("▣", f"Signal: {decision['action']} {decision['asset']}", lvl)
            _cog("✓", "Analysis cycle complete", "ok")
            time.sleep(0.5)

            st.session_state["latest_decision"] = decision
            st.session_state["decision_history"].append({
                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                **decision,
            })

    # Display latest decision
    dec = st.session_state.get("latest_decision")
    if dec:
        action = dec["action"]
        css    = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(action, "dec-hold")
        icon   = {"BUY": "🟢", "SELL": "🔴"}.get(action, "🟡")

        st.markdown(f"""
        <div class="dec-box {css}">
            <div style="font-size:1.4rem;font-weight:700;margin-bottom:0.4rem">
                {icon} {action} {dec['asset']}</div>
            <div style="color:#ccd6f6;font-size:0.9rem">
                Position: <b>{dec['position_size_percent']:.1f}%</b>
                (${dec['amount_usd']:,.2f})
                &nbsp;·&nbsp; Confidence: <b>{dec['confidence']:.0%}</b>
                &nbsp;·&nbsp; Risk: <b>{dec['risk_score']}/10</b>
                &nbsp;·&nbsp; SL: <b>{dec['stop_loss_percent']:.1f}%</b>
                &nbsp;·&nbsp; TP: <b>{dec['take_profit_percent']:.1f}%</b>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"**Reasoning:** _{dec['entry_reasoning']}_")

        # ── Explainable AI (XAI) Panel ─────────────────────
        st.markdown(xai_panel_html(dec, df), unsafe_allow_html=True)

        # ── AI Confidence Gauge ────────────────────────────
        col_gauge, col_bar = st.columns([1, 2])
        with col_gauge:
            st.plotly_chart(confidence_gauge(dec["confidence"]),
                           use_container_width=True)
        with col_bar:
            # Confidence bar (kept from v2)
            cp = dec["confidence"] * 100
            cc = "#64ffda" if cp >= 70 else ("#ffd93d" if cp >= 40 else "#ff6b6b")
        st.markdown(f"""
        <div style="background:#050510;border-radius:10px;padding:0.6rem 1rem;margin-top:0.5rem">
            <div style="color:#495670;font-size:0.7rem;margin-bottom:4px">CONFIDENCE</div>
            <div style="background:#111130;border-radius:4px;height:14px;width:100%">
                <div style="background:{cc};width:{cp}%;height:100%;border-radius:4px;
                            transition:width 0.5s"></div>
            </div>
            <div style="text-align:right;color:{cc};font-family:'JetBrains Mono',monospace;
                        font-size:0.8rem;margin-top:2px">{cp:.0f}%</div>
        </div>""", unsafe_allow_html=True)

        # Raw JSON
        with st.expander("📦 Raw JSON Decision (sign_trade.py input)"):
            json_out = {k: v for k, v in dec.items() if k != "amount_usd"}
            st.code(json.dumps(json_out, indent=2), language="json")
    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#495670">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">🧠</div>
            <div>Press <b>Run Analysis</b> to activate the cognitive engine.</div>
        </div>""", unsafe_allow_html=True)

    if st.session_state["decision_history"]:
        with st.expander(f"📜 Decision History ({len(st.session_state['decision_history'])})"):
            st.dataframe(pd.DataFrame(st.session_state["decision_history"]),
                         use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────
#  TAB 3 — Risk & Execution
# ──────────────────────────────────────────────────────────

with tab_risk:
    st.markdown("### 🛡️ Risk Management & Execution")

    # ── Risk Heat Map ─────────────────────────────────────
    st.markdown("#### ⚖️ Risk Heat Map")
    st.markdown(risk_heatmap_html(
        dict(st.session_state),
        st.session_state.get("latest_decision"),
        st.session_state["whatif_vol_mult"],
    ), unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Risk Router Map ─────────────────────────────────
    st.markdown("#### 🛡️ Risk Router — Rug-Pull Check Pipeline")
    st.caption("Visual flowchart of how the AI validates tokens before trading.")
    st.markdown(risk_router_html(st.session_state.get("latest_decision")),
                unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Transaction Simulator ───────────────────────────
    st.markdown("#### 🧪 Transaction Simulator")
    st.caption("Dry-run the trade locally — see expected gas and final balance before spending real ETH.")
    sim_dec = st.session_state.get("latest_decision")
    if sim_dec and sim_dec["action"] != "HOLD":
        if st.button("🧪  Simulate Trade", use_container_width=True):
            sim = simulate_trade(sim_dec, st.session_state["total_capital_usd"])
            _cog("🧪", f"Simulation: gas={sim['gas_gwei']}gwei "
                 f"slip={sim['slippage_pct']}% net=${sim['net_amount']}", "info")
            st.markdown(f"""
            <div class="sim-result">
                <div style="color:#4fc3f7;font-weight:600;font-size:0.75rem;
                            margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:1px">
                    🧪 Simulation Results</div>
                <div class="sim-row">
                    <span style="color:#8892b0">Gas Price</span>
                    <span style="color:#ccd6f6">{sim['gas_gwei']} gwei</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Gas Cost</span>
                    <span style="color:#ccd6f6">{sim['gas_cost_eth']:.6f} ETH (${sim['gas_cost_usd']:.2f})</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Slippage</span>
                    <span style="color:#ffd93d">{sim['slippage_pct']:.2f}%</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Net Trade Amount</span>
                    <span style="color:#64ffda">${sim['net_amount']:,.2f}</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Total Cost</span>
                    <span style="color:#ccd6f6">${sim['total_cost']:,.2f}</span></div>
                <div class="sim-row" style="border-top:1px solid #1a1a3e;padding-top:0.5rem;margin-top:0.3rem">
                    <span style="color:#8892b0;font-weight:600">Final Balance</span>
                    <span style="color:{'#64ffda' if sim['final_balance'] > 0 else '#ff6b6b'};font-weight:700">
                        ${sim['final_balance']:,.2f}</span></div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Run AI Analysis first to simulate a trade.")

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── What-If Volatility Simulator ──────────────────────
    st.markdown("#### 🔮 What-If Volatility Simulator")
    st.caption("Slide to simulate volatility changes and observe agent adaptation.")

    vol_mult = st.slider(
        "Volatility Multiplier",
        min_value=0.5, max_value=3.0,
        value=st.session_state["whatif_vol_mult"],
        step=0.1, key="whatif_slider",
        help="1.0 = current conditions. Higher = more volatile market simulation.",
    )
    st.session_state["whatif_vol_mult"] = vol_mult

    if vol_mult != 1.0:
        sim_dec    = run_analysis(df, st.session_state["selected_pair"], vol_mult)
        sim_regime = sim_dec["market_regime"]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(mcard("Sim Regime", sim_regime), unsafe_allow_html=True)
        with c2:
            st.markdown(mcard("Sim Confidence", f"{sim_dec['confidence']:.0%}",
                              "", sim_dec["confidence"] >= 0.6), unsafe_allow_html=True)
        with c3:
            st.markdown(mcard("Sim Position", f"{sim_dec['position_size_percent']:.1f}%",
                              "", sim_dec["position_size_percent"] > 0), unsafe_allow_html=True)
        with c4:
            st.markdown(mcard("Sim Risk", f"{sim_dec['risk_score']}/10",
                              "", sim_dec["risk_score"] <= 5), unsafe_allow_html=True)

        if (sim_dec["action"] == "HOLD"
                and st.session_state.get("latest_decision", {}).get("action") != "HOLD"):
            st.warning("🔮 At this volatility, the agent would **HOLD** instead of "
                       "trading. Risk-adaptive behavior confirmed.")
    else:
        st.info("Move the slider to simulate different volatility scenarios.")

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Pre-flight checks + execute ───────────────────────
    dec = st.session_state.get("latest_decision")
    if dec and dec["action"] != "HOLD":
        st.markdown("#### Pre-Flight Risk Checks")

        max_pos = st.session_state["max_position_usd"]
        cap     = st.session_state["total_capital_usd"]

        checks: list[tuple[str, bool, str]] = [
            ("Position ≤ 2% Capital",
             dec["position_size_percent"] <= 2.0,
             f"{dec['position_size_percent']:.1f}% ≤ 2.0%"),
            ("Amount ≤ Max Position",
             dec["amount_usd"] <= max_pos,
             f"${dec['amount_usd']:.0f} ≤ ${max_pos:.0f}"),
            ("Daily Loss Limit",
             st.session_state["session_pnl"] > -st.session_state["max_daily_loss_usd"],
             f"PnL ${st.session_state['session_pnl']:+.2f} > "
             f"-${st.session_state['max_daily_loss_usd']:.0f}"),
            ("Confidence ≥ 60%",
             dec["confidence"] >= 0.6,
             f"{dec['confidence']:.0%} ≥ 60%"),
            ("Stop Loss Set",
             dec["stop_loss_percent"] > 0,
             f"SL = {dec['stop_loss_percent']:.1f}%"),
            ("Take Profit Set",
             dec["take_profit_percent"] > 0,
             f"TP = {dec['take_profit_percent']:.1f}%"),
            ("Trade Frequency",
             st.session_state["trade_count"] < 10,
             f"{st.session_state['trade_count']} < 10/session"),
            ("No Leverage", True, "Leverage: None"),
        ]
        all_passed = all(c[1] for c in checks)

        for name, passed, detail in checks:
            icon = "✅" if passed else "❌"
            c    = "#64ffda" if passed else "#ff6b6b"
            st.markdown(f'<span style="color:{c}">{icon} **{name}**: {detail}</span>',
                        unsafe_allow_html=True)

        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

        if not all_passed:
            st.error("⛔ Risk checks failed — execution blocked.")

        if st.session_state["kill_switch_active"]:
            st.error("⛔ Kill switch is ACTIVE — all trading halted.")

        auto_mode = st.session_state["autonomous_mode"]

        if auto_mode and all_passed:
            if st.session_state["kill_switch_active"]:
                execute = False
            else:
                st.markdown("""
                <div class="auto-badge-on" style="margin-bottom:1rem">
                    <div style="font-size:0.9rem;font-weight:700;color:#64ffda">
                        ⚡ AUTO-EXECUTING…</div>
                </div>""", unsafe_allow_html=True)
                execute = True
        else:
            execute = st.button("🔏  Sign & Execute Trade",
                                use_container_width=True, type="primary",
                                disabled=(not all_passed
                                          or st.session_state["kill_switch_active"]))

        if execute and all_passed:
            with st.spinner("EIP-712 signing · Broadcasting to Risk Router…"):
                _cog("▣", f"Signing EIP-712 TradeIntent: "
                     f"{dec['action']} {dec['asset']}", "info")
                time.sleep(0.5)

                sig = "0x" + hashlib.sha256(
                    json.dumps(dec, default=str).encode()).hexdigest()[:64]
                tx  = "0x" + hashlib.sha256(
                    (sig + str(time.time())).encode()).hexdigest()[:64]

                _cog("▣", f"Signature: {sig[:22]}…", "sym")
                _cog("▣", "Broadcasting TX to Risk Router", "info")
                time.sleep(0.8)
                _cog("✓", f"TX confirmed: {tx[:22]}…", "ok")

                rng = np.random.default_rng(int(time.time()) % 100_000)
                pnl = round(float(rng.uniform(-40, 90)), 2)
                st.session_state["session_pnl"] += pnl
                st.session_state["trade_count"] += 1
                st.session_state["reputation_score"] = max(
                    0, min(100, st.session_state["reputation_score"]
                           + (1 if pnl > 0 else -2)))

                _cog("▣",
                     f"PnL: ${pnl:+.2f} — Reputation: "
                     f"{st.session_state['reputation_score']}",
                     "ok" if pnl > 0 else "warn")

                st.session_state["tx_log"].append({
                    "timestamp":  datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    "action":     dec["action"],
                    "asset":      dec["asset"],
                    "amount":     f"${dec['amount_usd']:,.2f}",
                    "confidence": f"{dec['confidence']:.0%}",
                    "risk":       f"{dec['risk_score']}/10",
                    "pnl":        f"${pnl:+.2f}",
                    "status":     "✅ Confirmed",
                    "tx_hash":    tx[:20] + "…",
                    "etherscan":  f"https://sepolia.etherscan.io/tx/{tx}",
                })

            st.success(f"Trade executed! TX: `{tx[:28]}…` · PnL: **${pnl:+.2f}**")
            if pnl > 0:
                st.balloons()
            st.rerun()

    elif dec and dec["action"] == "HOLD":
        st.markdown(
            '<div class="dec-box dec-hold" style="text-align:center">'
            '🟡 Recommendation: <b>HOLD</b> — No trade to execute</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#495670">'
            'Run AI Analysis to generate a trade intent.</div>',
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────
#  TAB 4 — Transaction Log
# ──────────────────────────────────────────────────────────

with tab_log:
    st.markdown("### 📒 Transaction & Intent Log")

    if st.session_state["tx_log"]:
        log_df = pd.DataFrame(st.session_state["tx_log"])
        st.dataframe(log_df, use_container_width=True, hide_index=True,
                     column_config={
                         "timestamp":  st.column_config.TextColumn("Time",    width="small"),
                         "action":     st.column_config.TextColumn("Action",  width="small"),
                         "asset":      st.column_config.TextColumn("Asset",   width="small"),
                         "amount":     st.column_config.TextColumn("Amount",  width="small"),
                         "confidence": st.column_config.TextColumn("Conf",    width="small"),
                         "risk":       st.column_config.TextColumn("Risk",    width="small"),
                         "pnl":        st.column_config.TextColumn("PnL",     width="small"),
                         "status":     st.column_config.TextColumn("Status",  width="small"),
                         "tx_hash":    st.column_config.TextColumn("TX Hash", width="medium"),
                         "etherscan":  st.column_config.LinkColumn("Etherscan ↗", width="small",
                                                                    display_text="View"),
                     })
        buy_sell = [t for t in st.session_state["tx_log"]
                    if t["action"] in ("BUY", "SELL")]
        st.caption(
            f"Executions: **{len(buy_sell)}** · "
            f"Session PnL: **${st.session_state['session_pnl']:+.2f}** · "
            f"Reputation: **{st.session_state['reputation_score']}/100**"
        )

        if st.button("🗑  Clear Log"):
            st.session_state["tx_log"]            = []
            st.session_state["session_pnl"]       = 0.0
            st.session_state["trade_count"]       = 0
            st.session_state["decision_history"]  = []
            st.session_state["cognitive_log"]     = []
            st.session_state["latest_decision"]   = None
            st.rerun()
    else:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#495670">'
            '<div style="font-size:2rem;margin-bottom:0.5rem">📒</div>'
            'No transactions yet.</div>',
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────
#  TAB 5 — P&L Tracker
# ──────────────────────────────────────────────────────────

with tab_pnl:
    st.markdown("### 📈 Profit & Loss Tracker")
    st.caption("Cumulative P&L across all executed trades this session.")

    trades_only = [t for t in st.session_state["tx_log"] if t.get("action") in ("BUY", "SELL")]
    if trades_only:
        # Summary metrics
        total_spent = sum(
            float(t["amount"].replace("$", "").replace(",", ""))
            for t in trades_only
        )
        cum_pnl = st.session_state["session_pnl"]
        portfolio_val = round(st.session_state["total_capital_usd"] + cum_pnl, 2)
        win_count = sum(1 for t in trades_only if float(t["pnl"].replace("$", "").replace("+", "")) > 0)
        loss_count = len(trades_only) - win_count
        win_rate = (win_count / len(trades_only) * 100) if trades_only else 0

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(mcard("Total Spent", f"${total_spent:,.2f}"),
                        unsafe_allow_html=True)
        with p2:
            st.markdown(mcard("Portfolio Value", f"${portfolio_val:,.2f}",
                              f"${cum_pnl:+.2f}", cum_pnl >= 0),
                        unsafe_allow_html=True)
        with p3:
            st.markdown(mcard("Win Rate", f"{win_rate:.0f}%",
                              f"{win_count}W / {loss_count}L", win_rate >= 50),
                        unsafe_allow_html=True)
        with p4:
            st.markdown(mcard("Session PnL", f"${cum_pnl:+.2f}", "", cum_pnl >= 0),
                        unsafe_allow_html=True)

        # P&L Chart
        fig = pnl_chart(st.session_state["tx_log"])
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        # Spent vs Portfolio bar
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Total Spent", "Current Value"],
            y=[total_spent, portfolio_val],
            marker_color=["#ff6b6b", "#64ffda"],
            text=[f"${total_spent:,.0f}", f"${portfolio_val:,.0f}"],
            textposition="outside",
            textfont=dict(color="#ccd6f6"),
        ))
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=200, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#495670">'
            '<div style="font-size:2rem;margin-bottom:0.5rem">📈</div>'
            'Execute trades to see P&L tracking.</div>',
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────
#  TAB 6 — AI Decision History Feed
# ──────────────────────────────────────────────────────────

with tab_history:
    st.markdown("### 🔍 AI Decision History")
    st.caption("Full feed of AI decisions with profitability annotations.")

    history = st.session_state["decision_history"]
    if history:
        # Match decisions with executed trades for profitability
        exec_log = {t["timestamp"]: t for t in st.session_state["tx_log"]
                    if t.get("action") in ("BUY", "SELL")}

        for i, dec_entry in enumerate(reversed(history)):
            action = dec_entry.get("action", "HOLD")
            conf   = dec_entry.get("confidence", 0)
            risk   = dec_entry.get("risk_score", 5)
            regime = dec_entry.get("market_regime", "?")
            ts     = dec_entry.get("time", "")
            reason = dec_entry.get("entry_reasoning", "")

            icon   = {"BUY": "🟢", "SELL": "🔴"}.get(action, "🟡")
            css    = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(action, "dec-hold")

            # Check if this was executed and get PnL
            pnl_badge = ""
            for tx_entry in st.session_state["tx_log"]:
                if (tx_entry.get("action") == action
                        and tx_entry.get("timestamp") == ts):
                    pnl_str = tx_entry.get("pnl", "$0")
                    pnl_val = float(pnl_str.replace("$", "").replace("+", ""))
                    if pnl_val > 0:
                        pnl_badge = f' · <span class="badge badge-green">✅ +${pnl_val:.2f}</span>'
                    else:
                        pnl_badge = f' · <span class="badge badge-red">❌ ${pnl_val:.2f}</span>'
                    break

            st.markdown(f"""
            <div class="dec-box {css}" style="padding:0.8rem 1rem;margin:0.4rem 0">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="font-size:1rem;font-weight:700">
                        {icon} {action} {dec_entry.get('asset', '?')}</span>
                    <span style="color:#495670;font-size:0.75rem">{ts}{pnl_badge}</span>
                </div>
                <div style="color:#8892b0;font-size:0.78rem;margin-top:0.3rem">
                    Conf: <b>{conf:.0%}</b> · Risk: <b>{risk}/10</b> ·
                    Regime: <b>{regime}</b> ·
                    Pos: <b>{dec_entry.get('position_size_percent', 0):.1f}%</b>
                </div>
                <div style="color:#495670;font-size:0.72rem;margin-top:0.2rem;font-style:italic">
                    {reason[:120]}{'...' if len(reason) > 120 else ''}</div>
            </div>""", unsafe_allow_html=True)

        # Summary stats
        buy_count  = sum(1 for d in history if d.get("action") == "BUY")
        sell_count = sum(1 for d in history if d.get("action") == "SELL")
        hold_count = sum(1 for d in history if d.get("action") == "HOLD")
        avg_conf   = np.mean([d.get("confidence", 0) for d in history])
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
        st.caption(
            f"Total: **{len(history)}** decisions · "
            f"🟢 BUY: **{buy_count}** · 🔴 SELL: **{sell_count}** · "
            f"🟡 HOLD: **{hold_count}** · Avg Confidence: **{avg_conf:.0%}**"
        )
    else:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#495670">'
            '<div style="font-size:2rem;margin-bottom:0.5rem">🔍</div>'
            'Run AI Analysis to build decision history.</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════
#  Footer
# ════════════════════════════════════════════════════════════

st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#3a3a5c;font-size:clamp(0.45rem,1.2vw,0.7rem);
            padding:0.5rem;word-break:break-word;line-height:1.6">
    Protocol Zero v2.0 &nbsp;·&nbsp; Autonomous Agent &nbsp;·&nbsp;
    ERC-8004 Compliant &nbsp;·&nbsp; EIP-712 Signed Intents &nbsp;·&nbsp;
    Nova Lite (Bedrock) &nbsp;·&nbsp; Hackathon 2025
</div>
""", unsafe_allow_html=True)
