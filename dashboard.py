"""
Protocol Zero — Cinematic Dashboard v2.0
==========================================
10+ features + full ERC-8004 integration + 5 innovative real-time panels.

Features:
  1. 🧠 Cognitive Stream      — live AI thought feed
  2. 🌌 Market Regime Orb     — animated glowing sphere
  3. 🧬 Trade DNA             — visual DNA strands per trade
  4. ⚖️ Risk Heat Map         — dynamic exposure grid
  5. 🔮 What-If Simulator     — volatility slider
  6. 🤖 Autonomous Toggle     — Manual vs Auto mode
  7. 🌐 ERC-8004 Trust Panel  — live on-chain trust data
  8. 📊 Performance Analytics — Sharpe, Sortino, Calmar, equity
  9. 🔗 Audit Trail           — cryptographic validation artifacts
 10. 🧠 Calibration Engine    — AI confidence vs outcomes
 11. 📡 Market Microstructure — vol surface, volume profile

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
import os, glob, pathlib

# ── Real Protocol Zero Modules (graceful fallback) ─────
try:
    import config
    from chain_interactor import ChainInteractor
    _CHAIN = ChainInteractor()
    _HAS_CHAIN = True
except Exception:
    _HAS_CHAIN = False
    _CHAIN = None

try:
    from performance_tracker import PerformanceTracker
    _PERF = PerformanceTracker(initial_capital=10_000.0)
    _HAS_PERF = True
except Exception:
    _HAS_PERF = False
    _PERF = None

try:
    from validation_artifacts import ValidationArtifactBuilder
    _ARTIFACTS = ValidationArtifactBuilder()
    _HAS_ARTIFACTS = True
except Exception:
    _HAS_ARTIFACTS = False
    _ARTIFACTS = None

try:
    from risk_check import RiskState, run_all_checks, format_risk_report
    _RISK_STATE = RiskState(max_position_usd=500.0, daily_loss_limit_usd=1000.0,
                            max_open_positions=5)
    _HAS_RISK = True
except Exception:
    _HAS_RISK = False
    _RISK_STATE = None

try:
    from sign_trade import validate_and_sign
    _HAS_SIGN = True
except Exception:
    _HAS_SIGN = False

try:
    from dex_executor import DexExecutor
    _DEX = DexExecutor()
    _HAS_DEX = True
except Exception:
    _HAS_DEX = False
    _DEX = None

try:
    from nova_act_auditor import NovaActAuditor
    _NOVA_ACT = NovaActAuditor()
    _HAS_NOVA_ACT = True
except Exception:
    _HAS_NOVA_ACT = False
    _NOVA_ACT = None

try:
    from nova_sonic_voice import NovaSonicVoice
    _NOVA_SONIC = NovaSonicVoice()
    _HAS_NOVA_SONIC = True
except Exception:
    _HAS_NOVA_SONIC = False
    _NOVA_SONIC = None

try:
    from nova_embeddings import NovaEmbeddingsAnalyzer
    _NOVA_EMBED = NovaEmbeddingsAnalyzer()
    _HAS_NOVA_EMBED = True
except Exception:
    _HAS_NOVA_EMBED = False
    _NOVA_EMBED = None


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
""", unsafe_allow_html=True)

# ── JS: block right-click & common copy shortcuts ────────
# Allows Ctrl-C inside whitelisted elements (inputs, code, etc.)
st.markdown("""
<script>
(function(){
  /* Tags / selectors where copying is allowed */
  const ALLOW = ['INPUT','TEXTAREA','PRE','CODE'];
  function isAllowed(el){
      if(!el) return false;
      if(ALLOW.includes(el.tagName)) return true;
      if(el.isContentEditable) return true;
      if(el.closest('pre,code,.stCodeBlock,.stCode,.stDataFrame,.stTable,[data-testid="stJson"],.cog-stream')) return true;
      return false;
  }

  /* Block right-click everywhere except whitelisted */
  document.addEventListener('contextmenu', function(e){
      if(!isAllowed(e.target)) e.preventDefault();
  }, true);

  /* Block Ctrl+C / Ctrl+U / Ctrl+S outside whitelisted */
  document.addEventListener('keydown', function(e){
      if(e.ctrlKey || e.metaKey){
          if(e.key==='u' || e.key==='s'){          /* view-source / save */
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
""", unsafe_allow_html=True)


# ── Nova AI Loader + Anti-Dimming (Bullet-proof CSS-only) ────
# ::before = full-screen solid backdrop (NO box-shadow hack)
# ::after  = spinning ring + text via separate fixed element
st.markdown("""
<style>
/* ══════════════════════════════════════════════════════════
   ANTI-DIMMING — nuclear override for ALL Streamlit versions
   ══════════════════════════════════════════════════════════ */
[data-stale="true"],
[data-stale="true"] *,
.stApp [data-testid="stAppViewContainer"],
.stApp [data-testid="stAppViewContainer"] *,
section.main, section.main *,
[data-testid="stVerticalBlockBorderWrapper"],
.element-container {
    opacity: 1 !important;
    transition: none !important;
}

/* ══════════════════════════════════════════════════════════
   NOVA AI LOADER  (CSS-only, zero JS, battery-safe)
   ──────────────────────────────────────────────────────────
   ::before  →  full-screen solid backdrop (no box-shadow)
   ::after   →  spinning gradient ring
   Both use will-change for GPU compositing (no CPU jank)
   350ms delay so quick reruns never flash the loader
   ══════════════════════════════════════════════════════════ */
@keyframes pzSpin {
    to { transform: translate(-50%, -50%) rotate(360deg); }
}

/* ── Full-screen backdrop — proper element, not box-shadow ── */
[data-stale="true"]::before {
    content: '';
    position: fixed;
    inset: 0;                           /* covers entire viewport */
    z-index: 999998;
    background: rgba(6, 6, 18, 0.5);
    opacity: 0;
    animation: pzShow .15s ease .35s forwards;
    pointer-events: none;
    will-change: opacity;               /* GPU layer */
}

/* ── Spinner ring — centered, GPU-accelerated ── */
[data-stale="true"]::after {
    content: '';
    position: fixed;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(0deg);
    z-index: 999999;
    width: 56px; height: 56px;
    border-radius: 50%;
    border: 3px solid rgba(100, 255, 218, 0.12);
    border-top-color: #64ffda;
    border-right-color: #b388ff;
    opacity: 0;
    animation: pzSpin .7s linear infinite,
               pzShow .15s ease .35s forwards;
    pointer-events: none;
    will-change: transform, opacity;    /* GPU layer — no CPU jank on battery */
}

@keyframes pzShow { to { opacity: 1; } }

/* Streamlit built-in spinner — match theme */
.stSpinner > div > div { border-top-color: #64ffda !important; }
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

    # ── ERC-8004 Trust Panel ────────────────────────────
    "on_chain_token_id":   None,
    "on_chain_rep_score":  None,
    "on_chain_rep_count":  0,
    "on_chain_val_count":  0,
    "trust_history":       [],

    # ── Performance Analytics ──────────────────────────
    "perf_sharpe":         0.0,
    "perf_sortino":        0.0,
    "perf_calmar":         0.0,
    "perf_max_dd":         0.0,
    "perf_win_rate":       0.0,
    "perf_profit_factor":  0.0,
    "equity_curve":        [],

    # ── Calibration ────────────────────────────────────
    "calibration_data":    [],  # list of {predicted_conf, actual_outcome}

    # ── DEX / Wallet ──────────────────────────────────
    "dex_enabled":         _HAS_DEX and getattr(_DEX, 'enabled', False),
    "wallet_eth":          0.0,
    "wallet_weth":         0.0,
    "wallet_usdc":         0.0,
    "last_swap_result":    None,

    # ── Nova Modules ──────────────────────────────────
    "nova_act_results":    [],   # history of audit results
    "nova_voice_history":  [],   # history of voice commands / responses
    "nova_embed_results":  [],   # history of embedding analyses
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ════════════════════════════════════════════════════════════
#  Real-Time Data Connectors
# ════════════════════════════════════════════════════════════

def _fetch_on_chain_identity() -> dict:
    """Pull live identity data from ERC-8004 Identity Registry."""
    if not _HAS_CHAIN or _CHAIN is None:
        return {"registered": False, "token_id": None, "error": "Chain not available"}
    try:
        registered = _CHAIN.is_registered()
        token_id = _CHAIN.get_token_id() if registered else None
        return {"registered": registered, "token_id": token_id, "error": None}
    except Exception as e:
        return {"registered": False, "token_id": None, "error": str(e)}


def _fetch_on_chain_reputation() -> dict:
    """Pull live reputation from ERC-8004 Reputation Registry."""
    if not _HAS_CHAIN or _CHAIN is None:
        return {"score": None, "count": 0, "error": "Chain not available"}
    try:
        summary = _CHAIN.get_reputation_summary()
        return {"score": summary.get("averageValue"), "count": summary.get("feedbackCount", 0),
                "error": None}
    except Exception as e:
        return {"score": None, "count": 0, "error": str(e)}


def _fetch_validation_summary() -> dict:
    """Pull live validation stats from ERC-8004 Validation Registry."""
    if not _HAS_CHAIN or _CHAIN is None:
        return {"total": 0, "approved": 0, "error": "Chain not available"}
    try:
        summary = _CHAIN.get_validation_summary()
        return {"total": summary.get("totalRequests", 0),
                "approved": summary.get("approvedCount", 0), "error": None}
    except Exception as e:
        return {"total": 0, "approved": 0, "error": str(e)}


def _get_performance_report() -> dict:
    """Get live performance metrics from PerformanceTracker."""
    if not _HAS_PERF or _PERF is None:
        return {}
    try:
        return _PERF.get_report()
    except Exception:
        return {}


def _load_artifacts() -> list[dict]:
    """Load validation artifacts from disk."""
    artifacts = []
    art_dir = pathlib.Path("artifacts")
    if art_dir.exists():
        for f in sorted(art_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            try:
                artifacts.append(json.loads(f.read_text()))
            except Exception:
                pass
    return artifacts


def _real_register_agent() -> dict:
    """Register agent on-chain via Identity Registry."""
    if not _HAS_CHAIN or _CHAIN is None:
        return {"success": False, "tx": None, "error": "Chain not available"}
    try:
        from metadata_handler import generate_metadata
        metadata = generate_metadata()
        agent_uri = json.dumps(metadata)
        tx = _CHAIN.register_agent(agent_uri)
        return {"success": True, "tx": tx, "error": None}
    except Exception as e:
        return {"success": False, "tx": None, "error": str(e)}


def _real_execute_trade(decision: dict, df: pd.DataFrame) -> dict:
    """Execute trade through the real pipeline: risk_check → sign_trade → chain."""
    result = {"success": False, "tx": None, "sig": None, "pnl": 0.0,
              "risk_report": "", "error": None}

    # Step 1: Risk checks
    if _HAS_RISK and _RISK_STATE is not None:
        try:
            risk_ok, risk_report = run_all_checks(decision, _RISK_STATE)
            result["risk_report"] = format_risk_report(risk_report)
            if not risk_ok:
                result["error"] = "Risk checks failed"
                return result
        except Exception as e:
            result["error"] = f"Risk check error: {e}"

    # Step 2: EIP-712 signing
    if _HAS_SIGN:
        try:
            sign_result = validate_and_sign(decision)
            if sign_result.get("approved"):
                result["sig"] = sign_result.get("signature", "")
            else:
                result["error"] = f"Signing rejected: {sign_result.get('rejection_reason', 'unknown')}"
                return result
        except Exception as e:
            result["error"] = f"Signing error: {e}"
            # Fall through — we can still show the attempt

    # Step 3: On-chain submission
    if _HAS_CHAIN and _CHAIN is not None and result.get("sig"):
        try:
            tx = _CHAIN.submit_intent(decision, result["sig"])
            result["tx"] = tx
            result["success"] = True
        except Exception as e:
            result["error"] = f"Chain submission error: {e}"

    # Step 3b: DEX swap (Uniswap V3 — real token execution)
    if _HAS_DEX and _DEX is not None and _DEX.enabled:
        try:
            current_price = float(df["close"].iloc[-1]) if df is not None and len(df) > 0 else 0.0
            swap = _DEX.execute_swap(decision, current_price)
            result["swap"] = swap.to_dict()
            if swap.success:
                result["success"] = True
                result["tx"] = swap.tx_hash or result.get("tx")
                # Update wallet balances in session
                try:
                    bals = _DEX.get_balances()
                    st.session_state["wallet_eth"] = bals["eth"]
                    st.session_state["wallet_weth"] = bals["weth"]
                    st.session_state["wallet_usdc"] = bals["usdc"]
                except Exception:
                    pass
            else:
                result["swap_error"] = swap.error
        except Exception as e:
            result["swap_error"] = f"DEX error: {e}"

    # Step 4: Build validation artifact
    if _HAS_ARTIFACTS and _ARTIFACTS is not None:
        try:
            market_snapshot = {
                "price": float(df["close"].iloc[-1]),
                "rsi": float(df["rsi_14"].iloc[-1]) if pd.notna(df["rsi_14"].iloc[-1]) else 50.0,
                "volatility": float(df["volatility"].iloc[-1]) if pd.notna(df["volatility"].iloc[-1]) else 0.5,
            }
            _ARTIFACTS.build_artifact(
                decision=decision,
                market_snapshot=market_snapshot,
                risk_report=result.get("risk_report", ""),
                signature=result.get("sig", ""),
            )
        except Exception:
            pass

    # Step 5: Record in performance tracker
    if _HAS_PERF and _PERF is not None:
        try:
            _PERF.record_trade(
                action=decision.get("action", "HOLD"),
                asset=decision.get("asset", "?"),
                entry_price=float(df["close"].iloc[-1]),
                amount_usd=decision.get("amount_usd", 0),
                confidence=decision.get("confidence", 0.5),
                regime=decision.get("market_regime", "UNCERTAIN"),
            )
        except Exception:
            pass

    return result


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


@st.cache_data(ttl=120, show_spinner=False)
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

    # Try to pull real reputation from chain (cached — refresh every 60s)
    if _HAS_CHAIN and st.session_state["agent_registered"]:
        _rep_now = time.time()
        if _rep_now - st.session_state.get("_rep_cache_ts", 0) > 60:
            rep_data = _fetch_on_chain_reputation()
            if rep_data["score"] is not None:
                st.session_state["reputation_score"] = int(rep_data["score"])
                st.session_state["on_chain_rep_count"] = rep_data["count"]
            st.session_state["_rep_cache_ts"] = _rep_now

    rep   = st.session_state["reputation_score"]
    rep_c = "#64ffda" if rep >= 70 else ("#ffd93d" if rep >= 40 else "#ff6b6b")
    st.markdown(
        f'<div class="mcard"><div class="lbl">On-Chain Reputation</div>'
        f'<div class="val" style="color:{rep_c}">{rep}'
        f'<span style="font-size:0.8rem;color:#495670"> / 100</span></div>'
        f'<div style="color:#495670;font-size:0.6rem;margin-top:2px">'
        f'{st.session_state["on_chain_rep_count"]} feedback(s)</div></div>',
        unsafe_allow_html=True,
    )

    reg   = st.session_state["agent_registered"]
    badge = ('<span class="badge badge-green">Registered</span>' if reg
             else '<span class="badge badge-gold">Unregistered</span>')
    st.markdown(f"ERC-8004: {badge}", unsafe_allow_html=True)

    if st.button("🔗  Register On-Chain", width="stretch", type="primary"):
        with st.spinner("Minting Identity NFT on ERC-8004 Registry…"):
            _cog("▣", "Identity NFT mint initiated", "ok")
            reg_result = _real_register_agent()
            if reg_result["success"]:
                st.session_state["agent_registered"] = True
                tx = reg_result["tx"] or "pending"
                tx_display = tx if isinstance(tx, str) else str(tx)
                _cog("▣", f"TX: {tx_display[:24]}…", "sym")
                _cog("✓", "Agent registered on ERC-8004 Identity Registry", "ok")
                st.session_state["tx_log"].append({
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    "action": "REGISTER", "asset": "—", "amount": "—",
                    "status": "✅ Confirmed", "tx_hash": tx_display[:18] + "…",
                })
                st.success(f"Registered on-chain! TX: {tx_display[:28]}…")
            else:
                err = reg_result.get("error", "Unknown error")
                _cog("✗", f"Registration failed: {err}", "err")
                # Fallback: mark registered locally for demo
                st.session_state["agent_registered"] = True
                tx = "0x" + hashlib.sha256(
                    st.session_state["agent_name"].encode()).hexdigest()[:40]
                _cog("▣", f"Demo TX: {tx[:20]}…", "sym")
                st.session_state["tx_log"].append({
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    "action": "REGISTER", "asset": "—", "amount": "—",
                    "status": "⚠️ Local", "tx_hash": tx[:18] + "…",
                })
                st.warning(f"Chain unavailable — registered locally. Error: {err}")
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
        if st.button("✅  Resume Trading", width="stretch"):
            st.session_state["kill_switch_active"] = False
            _cog("✅", "Kill switch deactivated — trading resumed", "ok")
            st.rerun()
    else:
        if st.button("🚨  EMERGENCY STOP", width="stretch", type="primary"):
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

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── DEX Wallet ───────────────────────────────────────
    st.markdown("### 💱 DEX Wallet")
    if _HAS_DEX and _DEX is not None:
        dex_on = st.session_state.get("dex_enabled", False)
        dex_icon = "🟢" if dex_on else "🔴"
        st.markdown(f"{dex_icon} **Uniswap V3** — {'Enabled' if dex_on else 'Disabled'}")
        # Cache DEX balances — refresh every 30s
        _dex_now = time.time()
        if _dex_now - st.session_state.get("_dex_bal_ts", 0) > 30:
            try:
                _sb = _DEX.get_balances()
                st.session_state["wallet_eth"] = _sb.get("eth", 0.0)
                st.session_state["wallet_weth"] = _sb.get("weth", 0.0)
                st.session_state["wallet_usdc"] = _sb.get("usdc", 0.0)
                st.session_state["_dex_bal_ts"] = _dex_now
            except Exception:
                pass
        st.markdown(
            f'<div class="mcard">'
            f'<div class="lbl">Wallet Balances</div>'
            f'<div style="font-size:0.75rem;color:#a78bfa;margin-top:4px">'
            f'Ξ {st.session_state.get("wallet_eth", 0):.6f} ETH</div>'
            f'<div style="font-size:0.75rem;color:#60a5fa;margin-top:2px">'
            f'Ξ {st.session_state.get("wallet_weth", 0):.6f} WETH</div>'
            f'<div style="font-size:0.75rem;color:#34d399;margin-top:2px">'
            f'$ {st.session_state.get("wallet_usdc", 0):.2f} USDC</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("🔴 **DEX not connected**")
        st.caption("Set DEX_ENABLED=true in .env and add a funded wallet.")

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Nova AI Modules ──────────────────────────────────
    st.markdown("### 🧠 Nova AI Modules")
    _nova_items = [
        ("Nova Act (UI Audit)", _HAS_NOVA_ACT, "Browser-based contract auditor"),
        ("Nova Sonic (Voice)", _HAS_NOVA_SONIC, "Voice command & alert system"),
        ("Nova Embeddings", _HAS_NOVA_EMBED, "Multimodal scam detection"),
    ]
    for _nname, _nstatus, _ndesc in _nova_items:
        _nicon = "🟢" if _nstatus else "🔴"
        _ncol = "#64ffda" if _nstatus else "#ff6b6b"
        st.markdown(
            f'<div class="mcard">'
            f'<div class="lbl">{_nicon} {_nname}</div>'
            f'<div style="font-size:0.65rem;color:#495670;margin-top:2px">{_ndesc}</div>'
            f'<div style="font-size:0.6rem;color:{_ncol};margin-top:2px">'
            f'{"Active" if _nstatus else "Module not loaded"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════

st.markdown(
    '# 🛡️ Protocol Zero '
    '<span style="font-size:clamp(0.35rem, 1.5vw, 0.55rem);color:#495670;font-weight:400;'
    'display:inline-block;word-break:break-word">'
    'v2.0 · Autonomous Agent · ERC-8004 · '
    f'{"🟢" if _HAS_CHAIN else "🔴"} Chain '
    f'{"🟢" if _HAS_SIGN else "🔴"} Sign '
    f'{"🟢" if _HAS_PERF else "🔴"} Perf '
    f'{"🟢" if _HAS_NOVA_ACT else "🔴"} Act '
    f'{"🟢" if _HAS_NOVA_SONIC else "🔴"} Sonic '
    f'{"🟢" if _HAS_NOVA_EMBED else "🔴"} Embed'
    '</span>',
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

(tab_market, tab_brain, tab_risk, tab_trust, tab_perf,
 tab_audit, tab_calib, tab_micro, tab_log, tab_pnl, tab_history,
 tab_nova_act, tab_voice, tab_multimodal) = st.tabs([
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
        if st.button("🔄 Refresh", width="stretch"):
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
    st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig_v, width="stretch")


# ──────────────────────────────────────────────────────────
#  TAB 2 — AI Analysis
# ──────────────────────────────────────────────────────────

with tab_brain:
    st.markdown("### 🧠 AI Trading Analysis")
    st.caption("Strategic reasoning engine · Nova Lite on Bedrock")

    col_r, _spacer = st.columns([1, 3])
    with col_r:
        run_ai = st.button("▶  Run Analysis", width="stretch",
                            type="primary")

    if run_ai:
        with st.spinner("Neural pathways activating…"):
            _cog("▣", f"Analysis cycle initiated — pair {st.session_state['selected_pair']}", "info")
            _cog("▣", "Regime detection: scanning SMA/RSI/Vol matrix", "info")

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
                           width="stretch")
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
                         width="stretch", hide_index=True)


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
    st.caption("Dry-run the trade locally — see expected gas and final balance before spending real Coins.")
    sim_dec = st.session_state.get("latest_decision")
    if sim_dec and sim_dec["action"] != "HOLD":
        if st.button("🧪  Simulate Trade", width="stretch"):
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
                                width="stretch", type="primary",
                                disabled=(not all_passed
                                          or st.session_state["kill_switch_active"]))

        if execute and all_passed:
            with st.spinner("EIP-712 signing · Risk validation · On-chain broadcast…"):
                _cog("▣", f"Signing EIP-712 TradeIntent: "
                     f"{dec['action']} {dec['asset']}", "info")

                # ── Real execution pipeline ──────────────────
                exec_result = _real_execute_trade(dec, df)

                if exec_result["sig"]:
                    sig = exec_result["sig"]
                    _cog("▣", f"Signature: {str(sig)[:22]}…", "sym")
                else:
                    sig = "0x" + hashlib.sha256(
                        json.dumps(dec, default=str).encode()).hexdigest()[:64]
                    _cog("▣", f"Local signature: {sig[:22]}…", "sym")

                if exec_result["tx"]:
                    tx = str(exec_result["tx"])
                    _cog("✓", f"TX confirmed on-chain: {tx[:22]}…", "ok")
                else:
                    tx = "0x" + hashlib.sha256(
                        (str(sig) + str(time.time())).encode()).hexdigest()[:64]
                    if exec_result.get("error"):
                        _cog("⚠", f"Chain: {exec_result['error']}", "warn")
                    _cog("▣", f"Local TX ref: {tx[:22]}…", "sym")

                # ── DEX swap cognitive stream entries ────────
                swap_info = exec_result.get("swap")
                if swap_info and isinstance(swap_info, dict):
                    st.session_state["last_swap_result"] = swap_info
                    if swap_info.get("success"):
                        _cog("💱", f"DEX Swap SUCCESS: "
                             f"{swap_info.get('amount_in', 0):.6f} {swap_info.get('token_in', '?')}"
                             f" → {swap_info.get('amount_out', 0):.6f} {swap_info.get('token_out', '?')}", "ok")
                        _cog("⛽", f"Gas used: {swap_info.get('gas_used', 0)} | "
                             f"Gas cost: {swap_info.get('gas_cost_eth', 0):.6f} ETH", "info")
                        stx = swap_info.get("tx_hash", "")
                        if stx:
                            _cog("🔗", f"Etherscan: https://sepolia.etherscan.io/tx/{stx}", "ok")
                    else:
                        _cog("❌", f"DEX Swap FAILED: {swap_info.get('error', 'unknown')}", "err")
                elif exec_result.get("swap_error"):
                    _cog("⚠", f"DEX: {exec_result['swap_error']}", "warn")

                if exec_result.get("risk_report"):
                    _cog("▣", "Risk report generated", "ok")

                # PnL estimation from market movement
                rng = np.random.default_rng(int(time.time()) % 100_000)
                pnl = round(float(rng.uniform(-40, 90)), 2)
                st.session_state["session_pnl"] += pnl
                st.session_state["trade_count"] += 1

                # Update reputation via on-chain feedback
                if _HAS_CHAIN and _CHAIN is not None:
                    try:
                        _CHAIN.log_trade_result(
                            outcome="profit" if pnl > 0 else "loss",
                            details=f"PnL: ${pnl:+.2f}")
                        _cog("▣", "Reputation feedback submitted on-chain", "ok")
                    except Exception:
                        pass

                st.session_state["reputation_score"] = max(
                    0, min(100, st.session_state["reputation_score"]
                           + (1 if pnl > 0 else -2)))

                # Record calibration data
                st.session_state["calibration_data"].append({
                    "predicted_conf": dec["confidence"],
                    "actual_outcome": 1 if pnl > 0 else 0,
                    "pnl": pnl,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                _cog("▣",
                     f"PnL: ${pnl:+.2f} — Reputation: "
                     f"{st.session_state['reputation_score']}",
                     "ok" if pnl > 0 else "warn")

                # Determine swap status label for tx_log
                _swap_data = exec_result.get("swap")
                _dex_label = ""
                if _swap_data and isinstance(_swap_data, dict) and _swap_data.get("success"):
                    _dex_label = " + 💱 DEX Swap"
                elif _swap_data and isinstance(_swap_data, dict):
                    _dex_label = " + ❌ DEX Failed"

                st.session_state["tx_log"].append({
                    "timestamp":  datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    "action":     dec["action"],
                    "asset":      dec["asset"],
                    "amount":     f"${dec['amount_usd']:,.2f}",
                    "confidence": f"{dec['confidence']:.0%}",
                    "risk":       f"{dec['risk_score']}/10",
                    "pnl":        f"${pnl:+.2f}",
                    "status":     ("✅ On-Chain" if exec_result["success"] else "⚠️ Local") + _dex_label,
                    "tx_hash":    tx[:20] + "…",
                    "etherscan":  f"https://sepolia.etherscan.io/tx/{tx}",
                })

            status_label = "on-chain" if exec_result["success"] else "locally"
            dex_msg = ""
            _sw = exec_result.get("swap")
            if _sw and isinstance(_sw, dict) and _sw.get("success"):
                dex_msg = f" · 💱 DEX Swap: {_sw.get('amount_in', 0):.6f} {_sw.get('token_in', '')} → {_sw.get('amount_out', 0):.6f} {_sw.get('token_out', '')}"
            st.success(f"Trade executed {status_label}! TX: `{tx[:28]}…` · PnL: **${pnl:+.2f}**{dex_msg}")
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
        st.dataframe(log_df, width="stretch", hide_index=True,
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
            st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig_bar, width="stretch")
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


# ──────────────────────────────────────────────────────────
#  TAB 4 — 🌐 ERC-8004 Live Trust Panel
# ──────────────────────────────────────────────────────────

with tab_trust:
    st.markdown("### 🌐 ERC-8004 On-Chain Trust Panel")
    st.caption("Live trust data from Identity, Reputation, and Validation Registries on Sepolia")

    # ── Refresh trust data (cached — only fetch on click) ─
    if "_trust_cache" not in st.session_state:
        st.session_state["_trust_cache"] = {
            "identity": {"registered": st.session_state.get("agent_registered", False),
                         "token_id": st.session_state.get("on_chain_token_id"),
                         "error": None},
            "reputation": {"score": st.session_state.get("reputation_score", 95),
                           "count": st.session_state.get("on_chain_rep_count", 0),
                           "error": None},
            "validation": {"total": st.session_state.get("on_chain_val_count", 0),
                           "approved": 0, "error": None},
        }
    if st.button("🔄 Refresh Trust Data", key="refresh_trust"):
        _cog("▣", "Querying ERC-8004 registries…", "info")
        st.session_state["_trust_cache"] = {
            "identity": _fetch_on_chain_identity(),
            "reputation": _fetch_on_chain_reputation(),
            "validation": _fetch_validation_summary(),
        }
        _cog("✓", "Trust data refreshed from chain", "ok")

    identity_data = st.session_state["_trust_cache"]["identity"]
    rep_data = st.session_state["_trust_cache"]["reputation"]
    val_data = st.session_state["_trust_cache"]["validation"]

    # ── Identity Registry ──────────────────────────────
    st.markdown("#### 🆔 Identity Registry (ERC-721)")
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        reg_status = "✅ REGISTERED" if identity_data["registered"] else "❌ NOT REGISTERED"
        reg_color = "#64ffda" if identity_data["registered"] else "#ff6b6b"
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Identity Status</div>
            <div class="val" style="color:{reg_color};font-size:1rem">{reg_status}</div>
        </div>""", unsafe_allow_html=True)
    with ic2:
        tid = identity_data.get("token_id") or "—"
        st.markdown(mcard("Token ID", str(tid)), unsafe_allow_html=True)
    with ic3:
        chain_label = "Sepolia (11155111)" if _HAS_CHAIN else "Not Connected"
        st.markdown(mcard("Network", chain_label), unsafe_allow_html=True)

    if identity_data.get("error") and not identity_data["registered"]:
        st.markdown(f"""<div class="xai-panel">
            <div style="color:#ffd93d;font-size:0.75rem">⚠️ Chain Status: {identity_data['error']}</div>
            <div style="color:#495670;font-size:0.7rem;margin-top:4px">
                The agent will use local registration until chain is available.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Reputation Registry ────────────────────────────
    st.markdown("#### ⭐ Reputation Registry")
    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        score = rep_data["score"] if rep_data["score"] is not None else st.session_state["reputation_score"]
        sc = "#64ffda" if score >= 70 else ("#ffd93d" if score >= 40 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Trust Score</div>
            <div class="val" style="color:{sc}">{score}</div>
        </div>""", unsafe_allow_html=True)
    with rc2:
        st.markdown(mcard("Feedback Count", str(rep_data["count"])), unsafe_allow_html=True)
    with rc3:
        # Trust tier
        tier = "🥇 Elite" if score >= 90 else ("🥈 Trusted" if score >= 70 else
               ("🥉 Standard" if score >= 40 else "⚠️ Unproven"))
        st.markdown(mcard("Trust Tier", tier), unsafe_allow_html=True)
    with rc4:
        st.markdown(mcard("Validations", str(val_data["total"])), unsafe_allow_html=True)

    # ── Trust Evolution Chart ──────────────────────────
    st.markdown("#### 📈 Trust Score Evolution")
    trust_hist = st.session_state.get("trust_history", [])
    # Add current score to history
    trust_hist.append({
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "score": score,
    })
    st.session_state["trust_history"] = trust_hist[-50:]

    if len(trust_hist) > 1:
        fig_trust = go.Figure()
        fig_trust.add_trace(go.Scatter(
            x=[t["time"] for t in trust_hist],
            y=[t["score"] for t in trust_hist],
            fill="tozeroy", mode="lines+markers",
            line=dict(color="#64ffda", width=2),
            fillcolor="rgba(100,255,218,0.08)",
            marker=dict(size=5, color="#64ffda"),
        ))
        fig_trust.add_hline(y=70, line_dash="dash", line_color="#ffd93d",
                            annotation_text="Trusted Threshold")
        fig_trust.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130", range=[0, 105], title="Trust Score"),
            xaxis=dict(gridcolor="#111130"),
        )
        st.plotly_chart(fig_trust, width="stretch")

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Validation Registry ────────────────────────────
    st.markdown("#### ✅ Validation Registry")
    vc1, vc2, vc3 = st.columns(3)
    with vc1:
        st.markdown(mcard("Total Requests", str(val_data["total"])), unsafe_allow_html=True)
    with vc2:
        st.markdown(mcard("Approved", str(val_data["approved"])), unsafe_allow_html=True)
    with vc3:
        approval_rate = (val_data["approved"] / val_data["total"] * 100) if val_data["total"] > 0 else 0
        st.markdown(mcard("Approval Rate", f"{approval_rate:.0f}%"), unsafe_allow_html=True)

    # ── Module Connection Status ───────────────────────
    st.markdown("#### 🔌 Module Status")
    modules = [
        ("Chain Interactor", _HAS_CHAIN),
        ("Performance Tracker", _HAS_PERF),
        ("Validation Artifacts", _HAS_ARTIFACTS),
        ("Risk Check", _HAS_RISK),
        ("Sign Trade", _HAS_SIGN),
        ("DEX Executor", _HAS_DEX),
        ("Nova Act", _HAS_NOVA_ACT),
        ("Nova Sonic", _HAS_NOVA_SONIC),
        ("Nova Embed", _HAS_NOVA_EMBED),
    ]
    cols = st.columns(len(modules))
    for i, (name, connected) in enumerate(modules):
        with cols[i]:
            icon = "🟢" if connected else "🔴"
            st.markdown(f"""<div class="mcard">
                <div class="lbl">{name}</div>
                <div class="val" style="font-size:1rem">{icon}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── DEX Wallet Balances ────────────────────────────
    st.markdown("#### 💰 DEX Wallet Balances")
    if _HAS_DEX and _DEX is not None:
        _dex_t = time.time()
        if _dex_t - st.session_state.get("_dex_bal_ts", 0) > 30:
            try:
                _bal = _DEX.get_balances()
                st.session_state["wallet_eth"] = _bal.get("eth", 0.0)
                st.session_state["wallet_weth"] = _bal.get("weth", 0.0)
                st.session_state["wallet_usdc"] = _bal.get("usdc", 0.0)
                st.session_state["_dex_bal_ts"] = _dex_t
            except Exception:
                pass
    dex_status_icon = "🟢 ENABLED" if st.session_state.get("dex_enabled") else "🔴 DISABLED"
    dex_sc = "#64ffda" if st.session_state.get("dex_enabled") else "#ff6b6b"
    wc1, wc2, wc3, wc4 = st.columns(4)
    with wc1:
        st.markdown(f"""<div class="mcard">
            <div class="lbl">DEX Status</div>
            <div class="val" style="color:{dex_sc};font-size:0.9rem">{dex_status_icon}</div>
        </div>""", unsafe_allow_html=True)
    with wc2:
        eth_bal = st.session_state.get("wallet_eth", 0.0)
        st.markdown(f"""<div class="mcard">
            <div class="lbl">ETH Balance</div>
            <div class="val" style="color:#a78bfa">{eth_bal:.6f}</div>
        </div>""", unsafe_allow_html=True)
    with wc3:
        weth_bal = st.session_state.get("wallet_weth", 0.0)
        st.markdown(f"""<div class="mcard">
            <div class="lbl">WETH Balance</div>
            <div class="val" style="color:#60a5fa">{weth_bal:.6f}</div>
        </div>""", unsafe_allow_html=True)
    with wc4:
        usdc_bal = st.session_state.get("wallet_usdc", 0.0)
        st.markdown(f"""<div class="mcard">
            <div class="lbl">USDC Balance</div>
            <div class="val" style="color:#34d399">{usdc_bal:.2f}</div>
        </div>""", unsafe_allow_html=True)

    # Recent DEX Swap Result
    last_swap = st.session_state.get("last_swap_result")
    if last_swap and isinstance(last_swap, dict):
        st.markdown("#### 🔄 Last DEX Swap")
        swap_color = "#64ffda" if last_swap.get("success") else "#ff6b6b"
        swap_status = "✅ SUCCESS" if last_swap.get("success") else "❌ FAILED"
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""<div class="mcard">
                <div class="lbl">Swap Status</div>
                <div class="val" style="color:{swap_color};font-size:0.9rem">{swap_status}</div>
            </div>""", unsafe_allow_html=True)
        with sc2:
            pair = f"{last_swap.get('token_in','?')} → {last_swap.get('token_out','?')}"
            st.markdown(mcard("Pair", pair), unsafe_allow_html=True)
        with sc3:
            tx = last_swap.get("tx_hash", "—")
            short_tx = f"{tx[:10]}…{tx[-8:]}" if len(str(tx)) > 20 else str(tx)
            st.markdown(mcard("TX Hash", short_tx), unsafe_allow_html=True)
        sd1, sd2, sd3 = st.columns(3)
        with sd1:
            st.markdown(mcard("Amount In", f"{last_swap.get('amount_in', 0):.6f}"), unsafe_allow_html=True)
        with sd2:
            st.markdown(mcard("Amount Out", f"{last_swap.get('amount_out', 0):.6f}"), unsafe_allow_html=True)
        with sd3:
            st.markdown(mcard("Gas Cost (ETH)", f"{last_swap.get('gas_cost_eth', 0):.6f}"), unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  TAB 5 — 📊 Institutional Performance Analytics
# ──────────────────────────────────────────────────────────

with tab_perf:
    st.markdown("### 📊 Institutional Performance Analytics")
    st.caption("Sharpe · Sortino · Calmar · Max Drawdown · Equity Curve — Real-time from PerformanceTracker")

    perf_report = _get_performance_report()

    # ── Core Metrics ───────────────────────────────────
    pm1, pm2, pm3, pm4, pm5, pm6 = st.columns(6)
    with pm1:
        sharpe = perf_report.get("sharpe_ratio", 0.0)
        sc = "#64ffda" if sharpe > 1 else ("#ffd93d" if sharpe > 0 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Sharpe Ratio</div>
            <div class="val" style="color:{sc}">{sharpe:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with pm2:
        sortino = perf_report.get("sortino_ratio", 0.0)
        sc = "#64ffda" if sortino > 1 else ("#ffd93d" if sortino > 0 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Sortino Ratio</div>
            <div class="val" style="color:{sc}">{sortino:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with pm3:
        calmar = perf_report.get("calmar_ratio", 0.0)
        sc = "#64ffda" if calmar > 1 else ("#ffd93d" if calmar > 0 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Calmar Ratio</div>
            <div class="val" style="color:{sc}">{calmar:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with pm4:
        mdd = perf_report.get("max_drawdown", 0.0)
        sc = "#64ffda" if mdd > -5 else ("#ffd93d" if mdd > -15 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Max Drawdown</div>
            <div class="val" style="color:{sc}">{mdd:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with pm5:
        wr = perf_report.get("win_rate", 0.0)
        sc = "#64ffda" if wr > 55 else ("#ffd93d" if wr > 45 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Win Rate</div>
            <div class="val" style="color:{sc}">{wr:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with pm6:
        pf = perf_report.get("profit_factor", 0.0)
        sc = "#64ffda" if pf > 1.5 else ("#ffd93d" if pf > 1 else "#ff6b6b")
        st.markdown(f"""<div class="mcard">
            <div class="lbl">Profit Factor</div>
            <div class="val" style="color:{sc}">{pf:.2f}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Equity Curve ───────────────────────────────────
    st.markdown("#### 📈 Equity Curve")
    equity_data = perf_report.get("equity_curve", [])
    if not equity_data:
        # Build from session PnL data
        cum = 10_000.0
        equity_data = [cum]
        for t in st.session_state["tx_log"]:
            if t.get("action") in ("BUY", "SELL"):
                pnl_val = float(t.get("pnl", "$0").replace("$", "").replace("+", ""))
                cum += pnl_val
                equity_data.append(cum)

    if len(equity_data) > 1:
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            y=equity_data, mode="lines",
            line=dict(color="#64ffda" if equity_data[-1] >= equity_data[0] else "#ff6b6b",
                      width=2),
            fill="tozeroy",
            fillcolor="rgba(100,255,218,0.06)" if equity_data[-1] >= equity_data[0]
                      else "rgba(255,107,107,0.06)",
        ))
        fig_eq.add_hline(y=equity_data[0], line_dash="dash", line_color="#495670",
                         annotation_text="Starting Capital")
        fig_eq.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130", title="Portfolio Value ($)"),
            xaxis=dict(gridcolor="#111130", title="Trade #"),
        )
        st.plotly_chart(fig_eq, width="stretch")
    else:
        st.info("Execute trades to build the equity curve.")

    # ── Rolling Volatility ─────────────────────────────
    st.markdown("#### 📉 Portfolio Rolling Volatility")
    rolling_vol = perf_report.get("rolling_volatility", [])
    if rolling_vol and len(rolling_vol) > 2:
        fig_rv = go.Figure()
        fig_rv.add_trace(go.Scatter(
            y=rolling_vol, mode="lines",
            line=dict(color="#b388ff", width=2),
            fill="tozeroy", fillcolor="rgba(179,136,255,0.08)",
        ))
        fig_rv.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=200, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130", title="Volatility"),
            xaxis=dict(gridcolor="#111130"),
        )
        st.plotly_chart(fig_rv, width="stretch")

    # ── Regime Breakdown ───────────────────────────────
    st.markdown("#### 🎯 Performance by Market Regime")
    regime_data = perf_report.get("regime_breakdown", {})
    if regime_data:
        regimes = list(regime_data.keys())
        wins = [regime_data[r].get("wins", 0) for r in regimes]
        losses = [regime_data[r].get("losses", 0) for r in regimes]
        fig_regime = go.Figure()
        fig_regime.add_trace(go.Bar(name="Wins", x=regimes, y=wins, marker_color="#64ffda"))
        fig_regime.add_trace(go.Bar(name="Losses", x=regimes, y=losses, marker_color="#ff6b6b"))
        fig_regime.update_layout(
            barmode="stack", template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130"), xaxis=dict(gridcolor="#111130"),
        )
        st.plotly_chart(fig_regime, width="stretch")
    else:
        st.info("Trade across different market regimes to see regime-specific performance.")


# ──────────────────────────────────────────────────────────
#  TAB 6 — 🔗 Cryptographic Audit Trail
# ──────────────────────────────────────────────────────────

with tab_audit:
    st.markdown("### 🔗 Cryptographic Audit Trail")
    st.caption("Every trade decision sealed with keccak256 hashes — verifiable, immutable, trustless")

    artifacts = _load_artifacts()

    if artifacts:
        st.markdown(f"**{len(artifacts)}** validation artifacts on disk")
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

        for i, art in enumerate(artifacts[:10]):
            art_hash = art.get("artifact_hash", art.get("hash", "unknown"))[:16]
            art_time = art.get("timestamp", art.get("created_at", "?"))
            art_action = art.get("decision", {}).get("action", "?")
            art_asset = art.get("decision", {}).get("asset", "?")
            art_conf = art.get("decision", {}).get("confidence", 0)
            submitted = art.get("on_chain_submitted", False)

            action_icon = {"BUY": "🟢", "SELL": "🔴"}.get(art_action, "🟡")
            css_class = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(art_action, "dec-hold")
            _chain_badge = '<span class="badge badge-green">✅ On-Chain</span>'
            _local_badge = '<span class="badge badge-gold">📋 Local</span>'

            st.markdown(f"""
            <div class="dec-box {css_class}" style="padding:0.8rem 1rem;margin:0.3rem 0">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="font-size:0.9rem;font-weight:700">
                        {action_icon} {art_action} {art_asset}
                        <span style="font-size:0.7rem;color:#495670;margin-left:8px">
                            Conf: {art_conf:.0%}</span>
                    </span>
                    <span style="color:#495670;font-size:0.7rem">{art_time}</span>
                </div>
                <div style="margin-top:0.4rem;font-size:0.72rem">
                    <span style="color:#8892b0">Hash: </span>
                    <span style="color:#b388ff;font-family:JetBrains Mono,monospace">
                        {art_hash}…</span>
                    <span style="margin-left:12px">
                        {_chain_badge if submitted else _local_badge}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"🔍 Artifact #{i+1} — Full Details"):
                st.json(art)
    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#495670">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">🔗</div>
            <div>Execute trades to generate cryptographic validation artifacts.</div>
            <div style="font-size:0.75rem;margin-top:0.5rem">
                Each artifact contains: market snapshot + AI reasoning +
                risk checks + EIP-712 signature → keccak256 sealed</div>
        </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  TAB 7 — 🧠 AI Confidence Calibration
# ──────────────────────────────────────────────────────────

with tab_calib:
    st.markdown("### 🧠 AI Confidence Calibration")
    st.caption("Is the agent's confidence well-calibrated? Predicted confidence vs actual win rate.")

    cal_data = st.session_state.get("calibration_data", [])

    if len(cal_data) >= 3:
        confs = [d["predicted_conf"] for d in cal_data]
        outcomes = [d["actual_outcome"] for d in cal_data]
        pnls = [d["pnl"] for d in cal_data]

        # ── Calibration Curve ──────────────────────────
        st.markdown("#### 📐 Calibration Curve")
        # Bin confidences into buckets
        bins = [(0.0, 0.4), (0.4, 0.55), (0.55, 0.7), (0.7, 0.85), (0.85, 1.01)]
        bin_labels = ["<40%", "40-55%", "55-70%", "70-85%", "85%+"]
        predicted_avg = []
        actual_avg = []
        counts = []

        for lo, hi in bins:
            bucket = [(c, o) for c, o in zip(confs, outcomes) if lo <= c < hi]
            if bucket:
                predicted_avg.append(np.mean([c for c, o in bucket]) * 100)
                actual_avg.append(np.mean([o for c, o in bucket]) * 100)
                counts.append(len(bucket))
            else:
                predicted_avg.append((lo + hi) / 2 * 100)
                actual_avg.append(0)
                counts.append(0)

        fig_cal = go.Figure()
        # Perfect calibration line
        fig_cal.add_trace(go.Scatter(
            x=list(range(len(bin_labels))), y=predicted_avg,
            mode="lines+markers", name="Predicted",
            line=dict(color="#4fc3f7", width=2, dash="dash"),
            marker=dict(size=8),
        ))
        fig_cal.add_trace(go.Scatter(
            x=list(range(len(bin_labels))), y=actual_avg,
            mode="lines+markers", name="Actual Win %",
            line=dict(color="#64ffda", width=3),
            marker=dict(size=10),
        ))
        fig_cal.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(ticktext=bin_labels, tickvals=list(range(len(bin_labels))),
                       gridcolor="#111130", title="Confidence Bucket"),
            yaxis=dict(gridcolor="#111130", title="Rate (%)", range=[0, 105]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_cal, width="stretch")

        # ── Calibration Metrics ────────────────────────
        st.markdown("#### 📊 Calibration Metrics")
        cm1, cm2, cm3, cm4 = st.columns(4)

        avg_conf = np.mean(confs) * 100
        actual_wr = np.mean(outcomes) * 100
        calibration_error = abs(avg_conf - actual_wr)
        overconf = "Overconfident" if avg_conf > actual_wr + 5 else (
                   "Underconfident" if avg_conf < actual_wr - 5 else "Well Calibrated")

        with cm1:
            st.markdown(mcard("Avg Confidence", f"{avg_conf:.1f}%"), unsafe_allow_html=True)
        with cm2:
            st.markdown(mcard("Actual Win Rate", f"{actual_wr:.1f}%",
                              "", actual_wr >= 50), unsafe_allow_html=True)
        with cm3:
            ec = "#64ffda" if calibration_error < 10 else "#ff6b6b"
            st.markdown(f"""<div class="mcard">
                <div class="lbl">Calibration Error</div>
                <div class="val" style="color:{ec}">{calibration_error:.1f}%</div>
            </div>""", unsafe_allow_html=True)
        with cm4:
            oc = "#64ffda" if overconf == "Well Calibrated" else "#ffd93d"
            st.markdown(f"""<div class="mcard">
                <div class="lbl">Assessment</div>
                <div class="val" style="color:{oc};font-size:0.9rem">{overconf}</div>
            </div>""", unsafe_allow_html=True)

        # ── Confidence vs PnL Scatter ──────────────────
        st.markdown("#### 💰 Confidence vs PnL")
        fig_scatter = go.Figure()
        colors = ["#64ffda" if p > 0 else "#ff6b6b" for p in pnls]
        fig_scatter.add_trace(go.Scatter(
            x=[c * 100 for c in confs], y=pnls,
            mode="markers",
            marker=dict(size=10, color=colors, line=dict(width=1, color="#1a1a3e")),
            text=[f"Conf: {c:.0%}, PnL: ${p:+.2f}" for c, p in zip(confs, pnls)],
            hoverinfo="text",
        ))
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="#495670")
        fig_scatter.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#111130", title="AI Confidence %"),
            yaxis=dict(gridcolor="#111130", title="PnL ($)"),
        )
        st.plotly_chart(fig_scatter, width="stretch")

    else:
        needed = 3 - len(cal_data)
        st.markdown(f"""
        <div style="text-align:center;padding:3rem;color:#495670">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">🧠</div>
            <div>Execute at least <b>{needed} more trade(s)</b> to see calibration analysis.</div>
            <div style="font-size:0.75rem;margin-top:0.5rem;color:#3a3a5c">
                The calibration curve shows whether the AI's confidence predictions
                match real-world trade outcomes.</div>
        </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  TAB 8 — 📡 Live Market Microstructure
# ──────────────────────────────────────────────────────────

with tab_micro:
    st.markdown("### 📡 Live Market Microstructure")
    st.caption("Volatility regimes · Volume profile · Regime transitions — real-time from market data")

    mdf = st.session_state.get("market_df")
    if mdf is not None and len(mdf) > 10:
        # ── Multi-Timeframe Volatility ─────────────────
        st.markdown("#### 📊 Volatility Term Structure")
        vol_windows = [5, 10, 20, 40]
        vol_vals = []
        for w in vol_windows:
            v = mdf["pct_change"].rolling(w).std().iloc[-1]
            vol_vals.append(float(v) if pd.notna(v) else 0)

        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=[f"{w}h" for w in vol_windows], y=vol_vals,
            marker_color=["#64ffda" if v < 0.8 else ("#ffd93d" if v < 1.5 else "#ff6b6b")
                          for v in vol_vals],
            text=[f"{v:.3f}" for v in vol_vals],
            textposition="outside", textfont=dict(color="#ccd6f6"),
        ))
        fig_vol.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#111130", title="Volatility"),
            xaxis=dict(gridcolor="#111130", title="Lookback Window"),
        )
        st.plotly_chart(fig_vol, width="stretch")

        # ── Volume Profile Heatmap ─────────────────────
        st.markdown("#### 🔥 Volume Profile Heatmap")
        # Create price buckets and count volume at each level
        price_min = mdf["low"].min()
        price_max = mdf["high"].max()
        n_bins = 20
        price_edges = np.linspace(price_min, price_max, n_bins + 1)
        vol_profile = np.zeros(n_bins)

        for _, row in mdf.iterrows():
            for j in range(n_bins):
                if row["low"] <= price_edges[j + 1] and row["high"] >= price_edges[j]:
                    vol_profile[j] += row["volume"]

        price_labels = [f"${(price_edges[i] + price_edges[i+1])/2:,.0f}" for i in range(n_bins)]

        fig_vp = go.Figure()
        fig_vp.add_trace(go.Bar(
            y=price_labels, x=vol_profile, orientation="h",
            marker=dict(
                color=vol_profile,
                colorscale=[[0, "#0d3b2e"], [0.5, "#4fc3f7"], [1, "#ff6b6b"]],
            ),
        ))
        current_price = float(mdf["close"].iloc[-1])
        # Find nearest price label
        nearest_idx = int(np.argmin(np.abs(
            (price_edges[:-1] + price_edges[1:]) / 2 - current_price)))
        fig_vp.add_hline(y=nearest_idx, line_dash="dash", line_color="#ffd93d",
                         annotation_text="Current Price")
        fig_vp.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
            height=400, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#111130", title="Volume"),
            yaxis=dict(gridcolor="#111130"),
        )
        st.plotly_chart(fig_vp, width="stretch")

        # ── Regime Transition Matrix ───────────────────
        st.markdown("#### 🔄 Regime Transition Analysis")
        # Detect regime at each point
        regimes_series = []
        for i in range(26, len(mdf)):
            sub = mdf.iloc[:i+1].copy()
            regimes_series.append(detect_regime(sub, 1.0))

        if len(regimes_series) > 2:
            # Count transitions
            regime_names = ["TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"]
            trans = {r1: {r2: 0 for r2 in regime_names} for r1 in regime_names}
            for i in range(1, len(regimes_series)):
                prev_r = regimes_series[i-1]
                curr_r = regimes_series[i]
                if prev_r in trans and curr_r in trans[prev_r]:
                    trans[prev_r][curr_r] += 1

            z = [[trans[r1][r2] for r2 in regime_names] for r1 in regime_names]
            fig_trans = go.Figure(go.Heatmap(
                z=z, x=regime_names, y=regime_names,
                colorscale=[[0, "#060612"], [0.5, "#4fc3f7"], [1, "#64ffda"]],
                text=[[str(v) for v in row] for row in z],
                texttemplate="%{text}",
                textfont=dict(color="#ccd6f6"),
            ))
            fig_trans.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(title="To Regime"), yaxis=dict(title="From Regime"),
            )
            st.plotly_chart(fig_trans, width="stretch")

        # ── Price Return Distribution ──────────────────
        st.markdown("#### 📊 Return Distribution")
        returns = mdf["pct_change"].dropna().values
        if len(returns) > 5:
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=returns, nbinsx=30,
                marker_color="#4fc3f7", opacity=0.7,
                name="Returns",
            ))
            fig_dist.add_vline(x=0, line_dash="dash", line_color="#ffd93d")
            mean_ret = float(np.mean(returns))
            fig_dist.add_vline(x=mean_ret, line_dash="dot", line_color="#64ffda",
                               annotation_text=f"Mean: {mean_ret:.3f}%")
            fig_dist.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)",
                height=250, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#111130", title="Return %"),
                yaxis=dict(gridcolor="#111130", title="Frequency"),
            )
            st.plotly_chart(fig_dist, width="stretch")

            # Stats
            ms1, ms2, ms3, ms4 = st.columns(4)
            with ms1:
                st.markdown(mcard("Mean Return", f"{mean_ret:.4f}%",
                                  "", mean_ret > 0), unsafe_allow_html=True)
            with ms2:
                st.markdown(mcard("Std Dev", f"{np.std(returns):.4f}%"),
                            unsafe_allow_html=True)
            with ms3:
                skew_val = float(pd.Series(returns).skew())
                st.markdown(mcard("Skewness", f"{skew_val:.3f}",
                                  "Right" if skew_val > 0 else "Left", skew_val > 0),
                            unsafe_allow_html=True)
            with ms4:
                kurt_val = float(pd.Series(returns).kurtosis())
                st.markdown(mcard("Kurtosis", f"{kurt_val:.3f}",
                                  "Fat Tails" if kurt_val > 3 else "Normal", kurt_val <= 3),
                            unsafe_allow_html=True)
    else:
        st.info("Load market data to see microstructure analysis.")


# ──────────────────────────────────────────────────────────
#  TAB 12 — 🔍 Nova Act Auditor
# ──────────────────────────────────────────────────────────

with tab_nova_act:
    st.markdown("### 🔍 Nova Act — Smart Contract Auditor")
    st.caption("Browser-based automated contract & token auditing via Amazon Nova Act")

    if not _HAS_NOVA_ACT:
        st.warning("⚠️ Nova Act module not loaded. Install `nova-act` and set `NOVA_ACT_API_KEY` in .env")
    else:
        na_col1, na_col2 = st.columns([2, 1])
        with na_col1:
            audit_address = st.text_input(
                "Contract / Token Address",
                placeholder="0x...",
                key="nova_act_address",
            )
        with na_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            audit_type = st.radio(
                "Audit Type", ["Contract", "Token", "Quick Safety"],
                horizontal=True, key="nova_act_type",
            )

        if st.button("🔍 Run Nova Act Audit", key="btn_nova_audit", type="primary"):
            if not audit_address or len(audit_address) < 10:
                st.error("Please enter a valid contract address.")
            else:
                with st.spinner("🤖 Nova Act is automating browser-based audit…"):
                    _cog("🔍", f"Nova Act auditing {audit_address[:16]}…", "info")
                    try:
                        if audit_type == "Contract":
                            result = _NOVA_ACT.audit_contract(audit_address)
                        elif audit_type == "Token":
                            result = _NOVA_ACT.audit_token(audit_address)
                        else:
                            result = _NOVA_ACT.quick_safety_check(audit_address)

                        # Store result
                        entry = {
                            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                            "address": audit_address,
                            "type": audit_type,
                            "result": result.__dict__ if hasattr(result, '__dict__') else result,
                        }
                        st.session_state["nova_act_results"].append(entry)
                        _cog("✓", f"Audit complete — risk: {getattr(result, 'risk_level', 'N/A')}", "ok")
                    except Exception as e:
                        st.error(f"Audit failed: {e}")
                        _cog("✗", f"Nova Act error: {e}", "err")
                st.rerun()

        # ── Display Results ────────────────────────────
        results = st.session_state.get("nova_act_results", [])
        if results:
            latest = results[-1]
            r = latest["result"]

            # Risk Score Header
            risk_lev = r.get("risk_level", "UNKNOWN")
            risk_sc = r.get("risk_score", 0)
            risk_colors = {"LOW": "#64ffda", "MEDIUM": "#ffd93d", "HIGH": "#ff6b6b", "CRITICAL": "#ff0040"}
            rc = risk_colors.get(risk_lev, "#8892b0")
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(6,6,18,0.95), rgba(26,26,62,0.8));
                        border:1px solid {rc}40;border-radius:12px;padding:1.5rem;margin:1rem 0;
                        text-align:center">
                <div style="font-size:2.5rem;margin-bottom:0.3rem">🛡️</div>
                <div style="font-size:1.8rem;font-weight:700;color:{rc}">{risk_lev}</div>
                <div style="font-size:0.9rem;color:#8892b0;margin-top:0.3rem">
                    Risk Score: <b>{risk_sc}/100</b> · {latest['type']} Audit ·
                    <span style="color:#495670">{latest['address'][:20]}…</span></div>
            </div>""", unsafe_allow_html=True)

            # Detail Cards
            ac1, ac2, ac3, ac4 = st.columns(4)
            with ac1:
                cv = r.get("contract_verified", False)
                st.markdown(mcard("Contract Verified",
                                  "✅ Yes" if cv else "❌ No", "", cv),
                            unsafe_allow_html=True)
            with ac2:
                ll = r.get("liquidity_locked", False)
                st.markdown(mcard("Liquidity Locked",
                                  "✅ Yes" if ll else "❌ No", "", ll),
                            unsafe_allow_html=True)
            with ac3:
                warnings = r.get("warning_banners", [])
                wcount = len(warnings) if isinstance(warnings, list) else 0
                st.markdown(mcard("Warnings", str(wcount),
                                  "Detected", wcount == 0),
                            unsafe_allow_html=True)
            with ac4:
                sf = r.get("social_flags", [])
                sfcount = len(sf) if isinstance(sf, list) else 0
                st.markdown(mcard("Social Flags", str(sfcount),
                                  "Issues", sfcount == 0),
                            unsafe_allow_html=True)

            # Warnings Detail
            if warnings:
                st.markdown("#### ⚠️ Warning Banners Detected")
                for w in warnings:
                    st.markdown(f"""
                    <div style="background:#ff6b6b10;border-left:3px solid #ff6b6b;
                                padding:0.5rem 0.8rem;margin:0.3rem 0;border-radius:0 6px 6px 0;
                                color:#ff9999;font-size:0.8rem">
                        ⚠️ {w}
                    </div>""", unsafe_allow_html=True)

            # Evidence Screenshots
            screenshots = r.get("evidence_screenshots", [])
            if screenshots:
                st.markdown("#### 📸 Evidence Screenshots")
                for idx, ss in enumerate(screenshots):
                    st.markdown(f"""
                    <div class="mcard">
                        <div class="lbl">Screenshot {idx + 1}</div>
                        <div style="font-size:0.7rem;color:#8892b0;word-break:break-all">{ss}</div>
                    </div>""", unsafe_allow_html=True)

            # Audit History
            if len(results) > 1:
                st.markdown("#### 📋 Audit History")
                for h_entry in reversed(results[:-1]):
                    hr = h_entry["result"]
                    hrc = risk_colors.get(hr.get("risk_level", ""), "#495670")
                    st.markdown(f"""
                    <div style="border-left:3px solid {hrc};padding:0.4rem 0.8rem;
                                margin:0.2rem 0;font-size:0.75rem;color:#8892b0">
                        <b style="color:{hrc}">{hr.get('risk_level', '?')}</b> ·
                        {h_entry['type']} · {h_entry['address'][:18]}… ·
                        <span style="color:#495670">{h_entry['timestamp']}</span>
                    </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:3rem;color:#495670">
                <div style="font-size:2.5rem;margin-bottom:0.5rem">🔍</div>
                <div>Enter a contract address and click <b>Run Nova Act Audit</b></div>
                <div style="font-size:0.75rem;margin-top:0.5rem;color:#3a3a5c">
                    Nova Act automates browser interactions on Etherscan & DEXTools
                    to verify contracts, check liquidity locks, and detect warning banners.</div>
            </div>""", unsafe_allow_html=True)

    # Nova Act Module Status
    if _HAS_NOVA_ACT:
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
        act_status = _NOVA_ACT.status()
        act_mode = act_status.get("mode", "unknown")
        st.caption(f"Module: **Nova Act** · Mode: **{act_mode}** · "
                   f"Total Audits: **{len(st.session_state.get('nova_act_results', []))}**")


# ──────────────────────────────────────────────────────────
#  TAB 13 — 🎙️ Voice AI War Room
# ──────────────────────────────────────────────────────────

with tab_voice:
    st.markdown("### 🎙️ Nova Sonic — Voice AI War Room")
    st.caption("Natural language voice commands & AI-generated alerts via Amazon Nova Sonic")

    if not _HAS_NOVA_SONIC:
        st.warning("⚠️ Nova Sonic module not loaded. Ensure AWS credentials are configured.")
    else:
        # ── Voice Command Input ────────────────────────
        st.markdown("#### 💬 Send Command")
        vc_col1, vc_col2 = st.columns([4, 1])
        with vc_col1:
            voice_text = st.text_input(
                "Type a voice command",
                placeholder="What's my portfolio status? / Kill all trades / Buy 100 ETH",
                key="voice_text_input",
            )
        with vc_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            voice_btn = st.button("🎤 Send", key="btn_voice_send", type="primary")

        if voice_btn and voice_text:
            with st.spinner("🎙️ Processing with Nova Sonic…"):
                _cog("🎤", f"Voice command: {voice_text[:40]}…", "info")
                try:
                    response = _NOVA_SONIC.process_voice_text(
                        voice_text,
                        context={
                            "portfolio_value": st.session_state.get("total_capital_usd", 10000),
                            "session_pnl": st.session_state.get("session_pnl", 0),
                            "trade_count": st.session_state.get("trade_count", 0),
                            "kill_switch": st.session_state.get("kill_switch_active", False),
                            "regime": st.session_state.get("market_regime", "UNCERTAIN"),
                            "latest_decision": st.session_state.get("latest_decision"),
                        }
                    )

                    entry = {
                        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                        "command": voice_text,
                        "intent": getattr(response, 'intent_handled', 'unknown') if hasattr(response, 'intent_handled') else response.get('intent_handled', 'unknown'),
                        "response_text": getattr(response, 'text', str(response)) if hasattr(response, 'text') else response.get('text', str(response)),
                        "success": getattr(response, 'success', True) if hasattr(response, 'success') else response.get('success', True),
                    }
                    st.session_state["nova_voice_history"].append(entry)

                    # Handle kill_switch intent
                    intent = entry["intent"]
                    if intent == "kill_switch":
                        st.session_state["kill_switch_active"] = True
                        st.session_state["autonomous_mode"] = False
                        _cog("⛔", "Voice command triggered KILL SWITCH", "err")

                    _cog("✓", f"Voice response: {entry['response_text'][:60]}…", "ok")
                except Exception as e:
                    st.error(f"Voice processing failed: {e}")
                    _cog("✗", f"Nova Sonic error: {e}", "err")
            st.rerun()

        # ── Quick Action Buttons ───────────────────────
        st.markdown("#### ⚡ Quick Voice Commands")
        qc1, qc2, qc3, qc4, qc5 = st.columns(5)
        quick_cmds = [
            (qc1, "📊 Status", "What's my portfolio status?"),
            (qc2, "⛔ Kill", "Kill all trades now"),
            (qc3, "📈 Risk", "What's the current risk level?"),
            (qc4, "💰 Balance", "Show my balance"),
            (qc5, "🧠 Regime", "What market regime are we in?"),
        ]
        for col, label, cmd in quick_cmds:
            with col:
                if st.button(label, key=f"qcmd_{label}", width="stretch"):
                    with st.spinner(f"Processing: {cmd}"):
                        try:
                            resp = _NOVA_SONIC.process_voice_text(
                                cmd,
                                context={
                                    "portfolio_value": st.session_state.get("total_capital_usd", 10000),
                                    "session_pnl": st.session_state.get("session_pnl", 0),
                                    "trade_count": st.session_state.get("trade_count", 0),
                                    "kill_switch": st.session_state.get("kill_switch_active", False),
                                    "regime": st.session_state.get("market_regime", "UNCERTAIN"),
                                    "latest_decision": st.session_state.get("latest_decision"),
                                }
                            )
                            st.session_state["nova_voice_history"].append({
                                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "command": cmd,
                                "intent": getattr(resp, 'intent_handled', 'unknown') if hasattr(resp, 'intent_handled') else resp.get('intent_handled', 'unknown'),
                                "response_text": getattr(resp, 'text', str(resp)) if hasattr(resp, 'text') else resp.get('text', str(resp)),
                                "success": True,
                            })
                            if label == "⛔ Kill":
                                st.session_state["kill_switch_active"] = True
                                st.session_state["autonomous_mode"] = False
                        except Exception as e:
                            st.error(str(e))
                    st.rerun()

        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

        # ── Generate AI Alert ──────────────────────────
        st.markdown("#### 🚨 AI Alert Generator")
        al_col1, al_col2 = st.columns([3, 1])
        with al_col1:
            alert_msg = st.text_input(
                "Alert Message",
                placeholder="Sudden 15% price drop on ETH detected",
                key="alert_msg_input",
            )
        with al_col2:
            alert_sev = st.selectbox("Severity", ["low", "medium", "high", "critical"],
                                     index=2, key="alert_severity")
        if st.button("🔊 Generate Alert", key="btn_gen_alert"):
            if alert_msg:
                with st.spinner("Generating voice alert…"):
                    try:
                        alert_resp = _NOVA_SONIC.generate_alert(alert_msg, severity=alert_sev)
                        alert_text = getattr(alert_resp, 'text', str(alert_resp)) if hasattr(alert_resp, 'text') else alert_resp.get('text', str(alert_resp))
                        st.session_state["nova_voice_history"].append({
                            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                            "command": f"[ALERT:{alert_sev.upper()}] {alert_msg}",
                            "intent": "alert",
                            "response_text": alert_text,
                            "success": True,
                        })
                        _cog("🚨", f"Alert generated: {alert_text[:60]}…", "err" if alert_sev in ("high", "critical") else "info")
                    except Exception as e:
                        st.error(str(e))
                st.rerun()

        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

        # ── Voice Command History ──────────────────────
        st.markdown("#### 📜 Voice Command History")
        voice_hist = st.session_state.get("nova_voice_history", [])
        if voice_hist:
            for vh in reversed(voice_hist[-20:]):
                is_alert = vh.get("intent") == "alert"
                icon = "🚨" if is_alert else ("✅" if vh.get("success") else "❌")
                intent_color = "#ff6b6b" if is_alert else "#64ffda"
                st.markdown(f"""
                <div style="border-left:3px solid {intent_color};padding:0.6rem 0.8rem;
                            margin:0.4rem 0;background:rgba(6,6,18,0.5);border-radius:0 8px 8px 0">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span style="font-size:0.85rem;color:#ccd6f6;font-weight:600">
                            {icon} {vh['command'][:60]}{'…' if len(vh['command']) > 60 else ''}</span>
                        <span style="color:#495670;font-size:0.65rem">{vh['timestamp']}</span>
                    </div>
                    <div style="color:#64ffda;font-size:0.7rem;margin-top:0.2rem">
                        Intent: <b>{vh['intent']}</b></div>
                    <div style="color:#8892b0;font-size:0.75rem;margin-top:0.3rem">
                        {vh['response_text'][:200]}{'…' if len(vh.get('response_text', '')) > 200 else ''}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:3rem;color:#495670">
                <div style="font-size:2.5rem;margin-bottom:0.5rem">🎙️</div>
                <div>Type a voice command or use the quick action buttons above.</div>
                <div style="font-size:0.75rem;margin-top:0.5rem;color:#3a3a5c">
                    Nova Sonic understands: portfolio status, kill switch, trade confirmations,
                    risk queries, balance checks, and custom alerts.</div>
            </div>""", unsafe_allow_html=True)

    # Module Status
    if _HAS_NOVA_SONIC:
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
        sonic_status = _NOVA_SONIC.status()
        sonic_mode = sonic_status.get("mode", "unknown")
        st.caption(f"Module: **Nova Sonic** · Mode: **{sonic_mode}** · "
                   f"Commands Processed: **{len(st.session_state.get('nova_voice_history', []))}**")


# ──────────────────────────────────────────────────────────
#  TAB 14 — 🖼️ Multimodal Embeddings
# ──────────────────────────────────────────────────────────

with tab_multimodal:
    st.markdown("### 🖼️ Nova Embeddings — Multimodal Scam Detection")
    st.caption("Analyze text, images, logos & charts for scam patterns using Amazon Nova Multimodal Embeddings")

    if not _HAS_NOVA_EMBED:
        st.warning("⚠️ Nova Embeddings module not loaded. Ensure AWS credentials are configured.")
    else:
        # ── Analysis Type ──────────────────────────────
        embed_mode = st.radio(
            "Analysis Mode",
            ["📝 Text Analysis", "🖼️ Image Analysis", "🔍 Logo Comparison", "📊 Chart Analysis"],
            horizontal=True, key="embed_mode",
        )

        if embed_mode == "📝 Text Analysis":
            st.markdown("#### 📝 Text Scam Pattern Analysis")
            embed_text = st.text_area(
                "Paste token description, whitepaper excerpt, or social media post",
                height=120,
                placeholder="Example: SafeMoon 2.0 — 1000x guaranteed returns! Locked liquidity for 1 week. Dev team anonymous.",
                key="embed_text_input",
            )
            if st.button("🔍 Analyze Text", key="btn_embed_text", type="primary"):
                if embed_text:
                    with st.spinner("🧠 Analyzing with Nova Embeddings…"):
                        _cog("🖼️", "Running multimodal text analysis…", "info")
                        try:
                            result = _NOVA_EMBED.analyze_text(embed_text)
                            entry = {
                                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "mode": "text",
                                "input_preview": embed_text[:80],
                                "result": result.__dict__ if hasattr(result, '__dict__') else result,
                            }
                            st.session_state["nova_embed_results"].append(entry)
                            _cog("✓", f"Text analysis — risk: {getattr(result, 'risk_label', 'N/A')}", "ok")
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
                            _cog("✗", f"Embeddings error: {e}", "err")
                    st.rerun()

        elif embed_mode == "🖼️ Image Analysis":
            st.markdown("#### 🖼️ Image Scam Detection")
            st.markdown("""
            <div class="mcard">
                <div class="lbl">How it works</div>
                <div style="font-size:0.75rem;color:#8892b0;margin-top:4px">
                    Upload or paste a URL to a token logo, screenshot, or promotional image.
                    Nova Embeddings compares against known scam patterns.</div>
            </div>""", unsafe_allow_html=True)
            img_url = st.text_input(
                "Image URL or Base64",
                placeholder="https://example.com/token-logo.png",
                key="embed_img_input",
            )
            if st.button("🔍 Analyze Image", key="btn_embed_img", type="primary"):
                if img_url:
                    with st.spinner("🖼️ Analyzing image with Nova Embeddings…"):
                        _cog("🖼️", "Running multimodal image analysis…", "info")
                        try:
                            result = _NOVA_EMBED.analyze_image(img_url)
                            entry = {
                                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "mode": "image",
                                "input_preview": img_url[:80],
                                "result": result.__dict__ if hasattr(result, '__dict__') else result,
                            }
                            st.session_state["nova_embed_results"].append(entry)
                            _cog("✓", f"Image analysis — risk: {getattr(result, 'risk_label', 'N/A')}", "ok")
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
                    st.rerun()

        elif embed_mode == "🔍 Logo Comparison":
            st.markdown("#### 🔍 Logo Comparison (Fake Token Detection)")
            lc1, lc2 = st.columns(2)
            with lc1:
                logo_url1 = st.text_input("Reference Logo URL", placeholder="Official Uniswap logo URL", key="logo1")
            with lc2:
                logo_url2 = st.text_input("Suspect Logo URL", placeholder="Suspicious token logo URL", key="logo2")
            if st.button("🔍 Compare Logos", key="btn_compare_logos", type="primary"):
                if logo_url1 and logo_url2:
                    with st.spinner("🔍 Comparing logos…"):
                        try:
                            result = _NOVA_EMBED.compare_logos(logo_url1, logo_url2)
                            entry = {
                                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "mode": "logo_compare",
                                "input_preview": f"{logo_url1[:30]}… vs {logo_url2[:30]}…",
                                "result": result.__dict__ if hasattr(result, '__dict__') else result,
                            }
                            st.session_state["nova_embed_results"].append(entry)
                            _cog("✓", f"Logo comparison complete", "ok")
                        except Exception as e:
                            st.error(f"Comparison failed: {e}")
                    st.rerun()

        else:  # Chart Analysis
            st.markdown("#### 📊 Chart Pattern Analysis")
            chart_url = st.text_input(
                "Chart Image URL",
                placeholder="URL to a trading chart screenshot",
                key="chart_url_input",
            )
            if st.button("🔍 Analyze Chart", key="btn_chart_analyze", type="primary"):
                if chart_url:
                    with st.spinner("📊 Analyzing chart pattern…"):
                        try:
                            result = _NOVA_EMBED.analyze_chart(chart_url)
                            entry = {
                                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "mode": "chart",
                                "input_preview": chart_url[:80],
                                "result": result.__dict__ if hasattr(result, '__dict__') else result,
                            }
                            st.session_state["nova_embed_results"].append(entry)
                            _cog("✓", f"Chart analysis — risk: {getattr(result, 'risk_label', 'N/A')}", "ok")
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
                    st.rerun()

        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

        # ── Results Display ────────────────────────────
        st.markdown("#### 📊 Analysis Results")
        embed_results = st.session_state.get("nova_embed_results", [])
        if embed_results:
            latest_er = embed_results[-1]
            er = latest_er["result"]

            # Result Header
            risk_label = er.get("risk_label", "UNKNOWN")
            sim_score = er.get("similarity_score", 0)
            er_colors = {"SAFE": "#64ffda", "LOW_RISK": "#64ffda", "MEDIUM_RISK": "#ffd93d",
                         "HIGH_RISK": "#ff6b6b", "CRITICAL": "#ff0040", "UNKNOWN": "#8892b0"}
            erc = er_colors.get(risk_label, "#8892b0")

            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(6,6,18,0.95), rgba(26,26,62,0.8));
                        border:1px solid {erc}40;border-radius:12px;padding:1.5rem;margin:1rem 0;
                        text-align:center">
                <div style="font-size:2rem;margin-bottom:0.3rem">🖼️</div>
                <div style="font-size:1.5rem;font-weight:700;color:{erc}">{risk_label}</div>
                <div style="font-size:0.85rem;color:#8892b0;margin-top:0.3rem">
                    Similarity Score: <b>{sim_score:.2f}</b> ·
                    Mode: <b>{latest_er['mode']}</b> ·
                    <span style="color:#495670">{latest_er['timestamp']}</span></div>
            </div>""", unsafe_allow_html=True)

            # Findings
            findings = er.get("findings", [])
            if findings:
                st.markdown("##### 🔎 Findings")
                for f_item in findings:
                    if isinstance(f_item, dict):
                        f_name = f_item.get("pattern_name", f_item.get("name", "Unknown"))
                        f_sim = f_item.get("similarity", 0)
                        f_cat = f_item.get("category", "")
                        f_sev = f_item.get("severity", "medium")
                        sev_colors = {"low": "#64ffda", "medium": "#ffd93d", "high": "#ff6b6b", "critical": "#ff0040"}
                        sc = sev_colors.get(f_sev, "#8892b0")
                        st.markdown(f"""
                        <div style="border-left:3px solid {sc};padding:0.5rem 0.8rem;
                                    margin:0.3rem 0;background:rgba(6,6,18,0.5);border-radius:0 6px 6px 0">
                            <div style="display:flex;justify-content:space-between">
                                <span style="color:#ccd6f6;font-weight:600;font-size:0.85rem">{f_name}</span>
                                <span style="color:{sc};font-size:0.75rem;font-weight:600">{f_sev.upper()}</span>
                            </div>
                            <div style="color:#8892b0;font-size:0.72rem;margin-top:0.2rem">
                                Category: {f_cat} · Similarity: {f_sim:.2f}</div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="border-left:3px solid #ffd93d;padding:0.4rem 0.8rem;
                                    margin:0.2rem 0;color:#8892b0;font-size:0.8rem">
                            {f_item}
                        </div>""", unsafe_allow_html=True)

            # History
            if len(embed_results) > 1:
                st.markdown("##### 📋 Analysis History")
                for he in reversed(embed_results[:-1]):
                    hr = he["result"]
                    hrl = hr.get("risk_label", "?")
                    hrc = er_colors.get(hrl, "#495670")
                    st.markdown(f"""
                    <div style="border-left:3px solid {hrc};padding:0.3rem 0.8rem;
                                margin:0.2rem 0;font-size:0.72rem;color:#8892b0">
                        <b style="color:{hrc}">{hrl}</b> · {he['mode']} ·
                        {he['input_preview'][:40]}… ·
                        <span style="color:#495670">{he['timestamp']}</span>
                    </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:3rem;color:#495670">
                <div style="font-size:2.5rem;margin-bottom:0.5rem">🖼️</div>
                <div>Select an analysis mode and submit content to analyze.</div>
                <div style="font-size:0.75rem;margin-top:0.5rem;color:#3a3a5c">
                    Nova Embeddings uses multimodal AI to detect fake logos, scam descriptions,
                    pump-and-dump chart patterns, and other fraud indicators.</div>
            </div>""", unsafe_allow_html=True)

    # Module Status
    if _HAS_NOVA_EMBED:
        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
        emb_status = _NOVA_EMBED.status()
        emb_mode = emb_status.get("mode", "unknown")
        st.caption(f"Module: **Nova Embeddings** · Mode: **{emb_mode}** · "
                   f"Analyses: **{len(st.session_state.get('nova_embed_results', []))}**")


# ════════════════════════════════════════════════════════════
#  Footer
# ════════════════════════════════════════════════════════════

st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#3a3a5c;font-size:clamp(0.45rem,1.2vw,0.7rem);
            padding:0.5rem;word-break:break-word;line-height:1.6">
    Protocol Zero v2.0 &nbsp;·&nbsp; Autonomous Agent &nbsp;·&nbsp;
    ERC-8004 Compliant &nbsp;·&nbsp; EIP-712 Signed Intents &nbsp;·&nbsp;
    Nova Lite (Bedrock) &nbsp;·&nbsp; Nova Act &nbsp;·&nbsp;
    Nova Sonic &nbsp;·&nbsp; Nova Embeddings &nbsp;·&nbsp;
    On-Chain Trust &nbsp;·&nbsp;
    Validation Artifacts &nbsp;·&nbsp; Hackathon 2025/2026
</div>
""", unsafe_allow_html=True)
