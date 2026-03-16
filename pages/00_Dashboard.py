from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

import app_core as core

# Initialize intro flag from localStorage if set
st.markdown("""
<script>
if (localStorage.getItem('pz_intro_done') === 'true') {
    window.streamlit_intro_done = true;
    localStorage.removeItem('pz_intro_done');
}
</script>
""", unsafe_allow_html=True)

# Show intro screen once per session
if not st.session_state.get("_intro_completed", False):
    core.render_intro_screen()
    st.session_state["_intro_completed"] = True
    st.stop()

df = core.render_shell(show_top_row=True)
flags = core.module_flags()

st.markdown("#### Panels")
core.render_panel_nav(str(st.session_state.get("active_panel", "📊  Market")))

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

st.markdown("#### Session Snapshot")
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

st.markdown("#### 🔌 Module Status")
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
