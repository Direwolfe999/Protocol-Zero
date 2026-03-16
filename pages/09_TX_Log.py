from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import app_core as core


core.render_shell(current_panel="📒  TX Log", show_top_row=True)

st.markdown("### 📒 Transaction & Intent Log")

if st.session_state.get("tx_log"):
	log_df = pd.DataFrame(st.session_state["tx_log"])
	st.dataframe(
		log_df,
		use_container_width=True,
		hide_index=True,
		column_config={
			"timestamp": st.column_config.TextColumn("Time", width="small"),
			"action": st.column_config.TextColumn("Action", width="small"),
			"asset": st.column_config.TextColumn("Asset", width="small"),
			"amount": st.column_config.TextColumn("Amount", width="small"),
			"confidence": st.column_config.TextColumn("Conf", width="small"),
			"risk": st.column_config.TextColumn("Risk", width="small"),
			"pnl": st.column_config.TextColumn("PnL", width="small"),
			"status": st.column_config.TextColumn("Status", width="small"),
			"tx_hash": st.column_config.TextColumn("TX Hash", width="medium"),
			"etherscan": st.column_config.LinkColumn("Etherscan ↗", width="small", display_text="View"),
		},
	)

	buy_sell = [t for t in st.session_state["tx_log"] if t.get("action") in ("BUY", "SELL")]
	st.caption(
		f"Executions: **{len(buy_sell)}** · Session PnL: **${st.session_state.get('session_pnl', 0.0):+.2f}** · Reputation: **{st.session_state.get('reputation_score', 95)}/100**"
	)

	c1, c2 = st.columns(2)
	with c1:
		csv = log_df.to_csv(index=False)
		st.download_button(
			"📥 Export CSV",
			data=csv,
			file_name=f"protocol_zero_txlog_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv",
			mime="text/csv",
			use_container_width=True,
		)
	with c2:
		if st.button("🗑 Clear Log", use_container_width=True):
			st.session_state["tx_log"] = []
			st.session_state["session_pnl"] = 0.0
			st.session_state["trade_count"] = 0
			st.session_state["decision_history"] = []
			st.session_state["cognitive_log"] = []
			st.session_state["latest_decision"] = None
else:
	st.info("No transactions yet.")

core.finalize_page()
