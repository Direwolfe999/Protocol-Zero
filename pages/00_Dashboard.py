from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

import app_core as core

# === PAGE CONFIGURATION (MUST BE FIRST) ===
st.set_page_config(page_title="Protocol Zero · Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Force intro for all non-skipped direct page access
if not st.session_state.get("_intro_completed", False):
    skip_intro = st.query_params.get("skip_intro") == "true"
    if not skip_intro:
        core.render_intro_screen()
        st.session_state["_intro_completed"] = True
        st.stop()
    st.session_state["_intro_completed"] = True

# === CUSTOM CSS ===
st.markdown("""
<style>
:root { --primary: #64ffda; --secondary: #3ec9ad; --dark: #0a0a1a; --card-bg: rgba(12,12,31,.95); }
* { margin: 0; padding: 0; box-sizing: border-box; }
.dashboard-header { background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%); 
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
    font-size: 2rem; font-weight: 800; margin-bottom: 1.5rem; }
.stat-card { background: var(--card-bg); border: 1px solid #1a1a3e; border-radius: 12px; padding: 1.2rem; 
    transition: all .3s; }
.stat-card:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(100,255,218,.1); }
.stat-label { color: #8892b0; font-size: .85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: .5rem; }
.stat-value { color: var(--primary); font-size: 1.8rem; font-weight: 700; }
.stat-unit { color: #495670; font-size: .9rem; margin-left: .5rem; }
.chevron { display: inline-block; margin-left: .5rem; animation: slideRight .3s ease; }
@keyframes slideRight { from { transform: translateX(-4px); opacity: .6; } to { transform: translateX(0); opacity: 1; } }
.mod-card { transition: all .2s; }
.mod-card:hover { transform: scale(1.05); }
.nav-section { margin: 2rem 0 1.5rem 0; padding-bottom: 1rem; border-bottom: 1px solid #1a1a3e; }
.nav-section h3 { color: var(--primary); font-size: .9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

df = core.render_shell(show_top_row=True)
flags = core.module_flags()

# === DASHBOARD HEADER ===
st.markdown('<div class="dashboard-header">⚡ Protocol Zero Dashboard</div>', unsafe_allow_html=True)

# === WALLET & BUDGET ROW ===
w1, w2, w3, w4 = st.columns(4)
with w1:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">💰 ETH Balance</div>
        <div class="stat-value">2.47 <span class="stat-unit">ETH</span></div>
    </div>
    """, unsafe_allow_html=True)
with w2:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">🔄 WETH Balance</div>
        <div class="stat-value">5.12 <span class="stat-unit">WETH</span></div>
    </div>
    """, unsafe_allow_html=True)
with w3:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">💵 USDC Balance</div>
        <div class="stat-value">15,847 <span class="stat-unit">USDC</span></div>
    </div>
    """, unsafe_allow_html=True)
with w4:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">📡 API Budget/Day</div>
        <div class="stat-value">487/500 <span class="stat-unit">calls</span></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# === SESSION METRICS ===
st.markdown('<div class="nav-section"><h3>📊 Session Metrics</h3></div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(core.mcard("Pair", str(st.session_state.get("selected_pair", "ETH/USDT"))), unsafe_allow_html=True)
with c2:
    st.markdown(core.mcard("Mode", "AUTO" if st.session_state.get("autonomous_mode") else "MANUAL"), unsafe_allow_html=True)
with c3:
    st.markdown(core.mcard("Trades", str(int(st.session_state.get("trade_count", 0)))), unsafe_allow_html=True)
with c4:
    pnl = float(st.session_state.get("session_pnl", 0.0))
    st.markdown(core.mcard("Session PnL", f"${pnl:+.2f}", up=pnl >= 0), unsafe_allow_html=True)

st.markdown("---")

# === STATE SNAPSHOT ===
st.markdown('<div class="nav-section"><h3>🔍 State Snapshot</h3></div>', unsafe_allow_html=True)
st.dataframe(
	{
		"selected_pair": [st.session_state.get("selected_pair")],
		"market_regime": [st.session_state.get("market_regime")],
		"reputation_score": [st.session_state.get("reputation_score")],
		"agent_registered": [st.session_state.get("agent_registered")],
		"tx_log_entries": [len(st.session_state.get("tx_log", []))],
		"decision_count": [len(st.session_state.get("decision_history", []))],
	},
	use_container_width=True,
	hide_index=True,
)

st.markdown("---")

# === MODULE STATUS ===
st.markdown('<div class="nav-section"><h3>🔌 Module Status</h3></div>', unsafe_allow_html=True)
mods = [
	("Chain Interactor", flags["has_chain"]),
	("Performance Tracker", flags["has_perf"]),
	("Validation Artifacts", flags["has_artifacts"]),
	("Risk Check", flags["has_risk"]),
	("Sign Trade", flags["has_sign"]),
	("DEX Executor", flags["has_dex"]),
	("Nova Act", flags["has_nova_act"]),
	("Nova Sonic", flags["has_nova_sonic"]),
	("Nova Embed", flags["has_nova_embed"]),
]

mod_cards = ""
for name, connected in mods:
	icon = "🟢" if connected else "🔴"
	cls = "mod-on" if connected else "mod-off"
	tag = "LIVE" if connected else "OFF"
	mod_cards += (
		f'<div class="mod-card {cls}">'
		f'<span class="mod-icon">{icon}</span>'
		f'<span class="mod-name">{name}</span>'
		f'<span class="mod-tag">{tag}</span>'
		f'</div>'
	)

st.markdown(f'<div class="mod-grid">{mod_cards}</div>', unsafe_allow_html=True)

core.finalize_page()
