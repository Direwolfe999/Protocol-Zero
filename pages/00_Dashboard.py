from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import app_core as core

# === PAGE CONFIG ===
st.set_page_config(page_title="Protocol Zero · Dashboard", layout="wide")

# === CUSTOM CSS WITH ANIMATIONS ===
st.markdown("""
<style>
:root { 
    --primary: #64ffda; --secondary: #3ec9ad; --dark: #0a0a1a; 
    --card-bg: rgba(12,12,31,.95); --danger: #ff4757; --success: #2ed573;
}
* { margin: 0; padding: 0; box-sizing: border-box; }

.dashboard-header { 
    background: linear-gradient(90deg, #64ffda 0%, #3ec9ad 100%); 
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
    font-size: 2.2rem; font-weight: 800; margin-bottom: 2rem; 
    display: flex; align-items: center; gap: 1rem;
}

.stat-card { 
    background: rgba(12,12,31,.95); border: 1px solid #1a1a3e; 
    border-radius: 12px; padding: 1.5rem; transition: all .3s;
}
.stat-card:hover { 
    border-color: #64ffda; transform: translateY(-4px); 
    box-shadow: 0 12px 32px rgba(100,255,218,.15);
}

.stat-label { color: #8892b0; font-size: .8rem; text-transform: uppercase; 
    letter-spacing: 1.5px; margin-bottom: .5rem; }
.stat-value { color: #64ffda; font-size: 2rem; font-weight: 800; }
.stat-unit { color: #495670; font-size: .9rem; margin-left: .5rem; }

.pulse-dot {
    display: inline-block; width: 12px; height: 12px; 
    background: #2ed573; border-radius: 50%; animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: .5; transform: scale(1.2); } }

.autonomous-badge {
    display: inline-block; padding: .5rem 1rem; 
    background: linear-gradient(90deg, #2ed573, #3ec9ad);
    color: #0a0a1a; border-radius: 20px; font-weight: 700;
    font-size: .9rem; margin-left: 1rem;
}

.tab-nav {
    display: flex; gap: .5rem; margin-bottom: 2rem; 
    padding: 1rem 0; border-bottom: 2px solid #1a1a3e;
    flex-wrap: wrap;
}

.tab-btn {
    padding: .75rem 1.5rem; background: transparent; border: none;
    color: #8892b0; cursor: pointer; font-size: .95rem; 
    transition: all .3s; border-bottom: 3px solid transparent;
    text-transform: uppercase; letter-spacing: 1px; font-weight: 600;
}

.tab-btn:hover, .tab-btn.active {
    color: #64ffda; border-bottom-color: #64ffda;
}

.chart-container {
    background: rgba(12,12,31,.95); border: 1px solid #1a1a3e;
    border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
}

.mod-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem; margin-top: 1rem;
}

.mod-card {
    background: rgba(12,12,31,.95); border: 1px solid #1a1a3e;
    border-radius: 12px; padding: 1.2rem; text-align: center;
    transition: all .3s;
}

.mod-card.active { 
    border-color: #2ed573; box-shadow: 0 0 16px rgba(46,213,115,.3);
}

.mod-card.inactive {
    border-color: #ff4757; box-shadow: 0 0 16px rgba(255,71,87,.3);
}

.mod-icon { font-size: 1.8rem; display: block; margin-bottom: .5rem; }
.mod-name { color: #ccd6f6; font-weight: 700; font-size: .95rem; }
.mod-status { font-size: .8rem; color: #8892b0; margin-top: .5rem; }

.toggle-switch {
    display: inline-block; width: 50px; height: 28px;
    background: #1a1a3e; border-radius: 14px; cursor: pointer;
    position: relative; transition: all .3s;
}

.toggle-switch.on {
    background: #2ed573;
}

.toggle-switch .toggle-circle {
    position: absolute; width: 24px; height: 24px;
    background: white; border-radius: 50%;
    top: 2px; left: 2px; transition: left .3s;
}

.toggle-switch.on .toggle-circle {
    left: 24px;
}
</style>

<script>
function toggleAutonomous() {
    const elem = document.querySelector('.toggle-switch');
    elem.classList.toggle('on');
}
</script>
""", unsafe_allow_html=True)

# Initialize session state
if "autonomous_mode" not in st.session_state:
    st.session_state.autonomous_mode = False
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "overview"

# === HEADER WITH MODE TOGGLE ===
col1, col2 = st.columns([0.7, 0.3])
with col1:
    st.markdown('<div class="dashboard-header">⚡ Protocol Zero Dashboard</div>', unsafe_allow_html=True)
with col2:
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.checkbox("Autonomous Mode", value=st.session_state.autonomous_mode):
            st.session_state.autonomous_mode = True
        else:
            st.session_state.autonomous_mode = False
    with c2:
        if st.session_state.autonomous_mode:
            st.markdown('<span class="pulse-dot"></span> <b style="color: #2ed573;">LIVE</b>', unsafe_allow_html=True)

# === WALLET BALANCES ===
st.markdown('<h3 style="color: #64ffda; margin-top: 2rem; margin-bottom: 1rem;">💼 Wallet & Balances</h3>', unsafe_allow_html=True)

w1, w2, w3, w4 = st.columns(4)
with w1:
    bal_eth = 2.47 + np.random.random() * 0.1
    st.metric("💰 ETH", f"{bal_eth:.3f}", "↑ 0.02", help="Ethereum balance on Sepolia")
with w2:
    bal_weth = 5.12 + np.random.random() * 0.1
    st.metric("🔄 WETH", f"{bal_weth:.3f}", "→ 0.00", help="Wrapped ETH balance")
with w3:
    bal_usdc = 15847 + int(np.random.random() * 100)
    st.metric("💵 USDC", f"${bal_usdc:,.0f}", "↑ 50", help="USDC balance for trading")
with w4:
    api_used = 487
    api_total = 500
    st.metric("📡 API/Day", f"{api_used}/{api_total}", f"{100-int(api_used/api_total*100)}%", help="Daily API call budget")

st.markdown("---")

# === TABS NAVIGATION ===
st.markdown('<h3 style="color: #64ffda; margin-bottom: 1rem;">📊 Panels</h3>', unsafe_allow_html=True)

tab_col1, tab_col2, tab_col3, tab_col4, tab_col5 = st.columns(5)
tabs = {
    "overview": ("📈 Overview", tab_col1),
    "market": ("📊 Market", tab_col2),
    "trading": ("🤖 Trading", tab_col3),
    "risk": ("⚠️ Risk", tab_col4),
    "performance": ("💹 Performance", tab_col5),
}

for tab_id, (tab_name, tab_col) in tabs.items():
    with tab_col:
        if st.button(tab_name, key=f"tab_{tab_id}", use_container_width=True):
            st.session_state.current_tab = tab_id

st.markdown("---")

# === CONTENT BASED ON TAB ===
if st.session_state.current_tab == "overview":
    st.markdown('<h3 style="color: #64ffda;">📈 Session Overview</h3>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Trades", 42, "↑ 5 today")
    m2.metric("Win Rate", "68%", "↑ 3%")
    m3.metric("Session P&L", "$2,847", "↑ 12%", delta_color="inverse")
    m4.metric("Reputation", "9.2/10", "↑ 0.3")
    
    # Market chart
    st.markdown('<div class="chart-container"><h4>💹 Price Action (Last 24h)</h4>', unsafe_allow_html=True)
    dates = pd.date_range('2024-01-01', periods=24, freq='H')
    eth_prices = 2200 + np.cumsum(np.random.randn(24) * 20)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=eth_prices, mode='lines+markers', 
        name='ETH/USDT', line=dict(color='#64ffda', width=3)))
    fig.update_layout(
        template='plotly_dark', hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#1a1a3e'), yaxis=dict(gridcolor='#1a1a3e'),
        margin=dict(l=0, r=0, t=0, b=0), height=300
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.current_tab == "market":
    st.markdown('<h3 style="color: #64ffda;">📊 Market Analysis</h3>', unsafe_allow_html=True)
    
    pairs = ["ETH/USDT", "BTC/USDT", "ARB/USDT", "OP/USDT"]
    prices = [2247.5, 43200, 1.89, 2.15]
    changes = [2.3, 1.8, -0.5, 3.2]
    
    market_df = pd.DataFrame({
        "Pair": pairs,
        "Price": prices,
        "24h Change %": changes,
        "Volume": [f"${x:.0f}M" for x in np.random.uniform(100, 500, 4)]
    })
    st.dataframe(market_df, use_container_width=True, hide_index=True)

elif st.session_state.current_tab == "trading":
    st.markdown('<h3 style="color: #64ffda;">🤖 Trading Activity</h3>', unsafe_allow_html=True)
    
    trades = pd.DataFrame({
        "Entry Time": pd.date_range('2024-01-01', periods=5, freq='H'),
        "Pair": ["ETH/USDT"] * 5,
        "Side": ["LONG", "SHORT", "LONG", "LONG", "SHORT"],
        "Size": [1.5, 2.0, 1.2, 1.8, 1.5],
        "Entry": [2240, 2250, 2235, 2245, 2255],
        "Exit": [2250, 2245, 2250, 2240, 2250],
        "P&L": ["+$150", "-$100", "+$180", "-$90", "+$225"],
    })
    st.dataframe(trades, use_container_width=True, hide_index=True)

elif st.session_state.current_tab == "risk":
    st.markdown('<h3 style="color: #64ffda;">⚠️ Risk Metrics</h3>', unsafe_allow_html=True)
    
    risk_cols = st.columns(3)
    risk_cols[0].metric("Max Drawdown", "-4.2%", "↓ -0.5%", delta_color="inverse")
    risk_cols[1].metric("Sharpe Ratio", "2.14", "↑ 0.12")
    risk_cols[2].metric("Sortino Ratio", "3.42", "↑ 0.25")
    
    exposure_data = pd.DataFrame({
        "Asset": ["ETH", "WETH", "USDC", "ARB"],
        "Exposure %": [35, 25, 30, 10],
    })
    st.bar_chart(exposure_data.set_index("Asset"), use_container_width=True)

elif st.session_state.current_tab == "performance":
    st.markdown('<h3 style="color: #64ffda;">💹 Performance Metrics</h3>', unsafe_allow_html=True)
    
    perf_cols = st.columns(4)
    perf_cols[0].metric("Total Return", "+47.3%", "↑ 5.2%")
    perf_cols[1].metric("Avg Trade", "+$67.71", "↑ $12")
    perf_cols[2].metric("Best Trade", "+$847", "💎")
    perf_cols[3].metric("Win/Loss", "42/21", "2:1")

st.markdown("---")

# === MODULE STATUS ===
st.markdown('<h3 style="color: #64ffda; margin-top: 2rem;">🔌 System Status</h3>', unsafe_allow_html=True)

mods = [
    ("Chain", flags["has_chain"]),
    ("Performance", flags["has_perf"]),
    ("Validation", flags["has_artifacts"]),
    ("Risk", flags["has_risk"]),
    ("Sign", flags["has_sign"]),
    ("DEX", flags["has_dex"]),
    ("Nova Act", flags["has_nova_act"]),
    ("Nova Sonic", flags["has_nova_sonic"]),
]

mod_cols = st.columns(len(mods))
for (name, status), col in zip(mods, mod_cols):
    with col:
        status_class = "active" if status else "inactive"
        status_text = "🟢 LIVE" if status else "🔴 OFF"
        st.markdown(f"""
        <div class="mod-card {status_class}">
            <div class="mod-name">{name}</div>
            <div class="mod-status">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

core.finalize_page()
