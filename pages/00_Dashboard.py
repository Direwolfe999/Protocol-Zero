from __future__ import annotations

import streamlit as st

import app_core as core


df = core.render_shell(show_top_row=True)

st.markdown("### 🏠 Operations Dashboard")
st.caption("Multipage home with shared runtime state and real-time controls")

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

st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
st.markdown("#### Quick Navigation")

qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
	if st.button("📊 Market", use_container_width=True):
		st.switch_page("pages/01_Market.py")
with qa2:
	if st.button("🧠 AI Brain", use_container_width=True):
		st.switch_page("pages/02_AI_Brain.py")
with qa3:
	if st.button("🛡️ Risk & Exec", use_container_width=True):
		st.switch_page("pages/03_Risk_Execution.py")
with qa4:
	if st.button("📊 Performance", use_container_width=True):
		st.switch_page("pages/05_Performance.py")

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

core.finalize_page()
