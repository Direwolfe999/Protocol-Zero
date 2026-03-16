from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import app_core as core


core.render_shell(current_panel="📈  P&L", show_top_row=True)

st.markdown("### 📈 Profit & Loss Tracker")
st.caption("Cumulative P&L across all executed trades this session")

trades = [t for t in st.session_state.get("tx_log", []) if t.get("action") in ("BUY", "SELL")]

if trades:
	total_spent = sum(float(str(t.get("amount", "$0")).replace("$", "").replace(",", "")) for t in trades)
	cum_pnl = float(st.session_state.get("session_pnl", 0.0))
	portfolio = round(float(st.session_state.get("total_capital_usd", 10000.0)) + cum_pnl, 2)
	win_count = sum(1 for t in trades if core._safe_pnl_value(t.get("pnl", "$0")) > 0)
	loss_count = len(trades) - win_count
	win_rate = (win_count / len(trades) * 100) if trades else 0

	p1, p2, p3, p4 = st.columns(4)
	with p1:
		st.markdown(core.mcard("Total Spent", f"${total_spent:,.2f}"), unsafe_allow_html=True)
	with p2:
		st.markdown(core.mcard("Portfolio Value", f"${portfolio:,.2f}", f"${cum_pnl:+.2f}", cum_pnl >= 0), unsafe_allow_html=True)
	with p3:
		st.markdown(core.mcard("Win Rate", f"{win_rate:.0f}%", f"{win_count}W/{loss_count}L", win_rate >= 50), unsafe_allow_html=True)
	with p4:
		st.markdown(core.mcard("Session PnL", f"${cum_pnl:+.2f}", up=cum_pnl >= 0), unsafe_allow_html=True)

	fig = core.pnl_chart(st.session_state.get("tx_log", []))
	if fig:
		st.plotly_chart(fig, use_container_width=True)

	fig_bar = go.Figure()
	fig_bar.add_trace(
		go.Bar(
			x=["Total Spent", "Current Value"],
			y=[total_spent, portfolio],
			marker_color=["#ff6b6b", "#64ffda"],
			text=[f"${total_spent:,.0f}", f"${portfolio:,.0f}"],
			textposition="outside",
		)
	)
	fig_bar.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=220, margin=dict(l=0, r=0, t=10, b=0))
	st.plotly_chart(fig_bar, use_container_width=True)
else:
	st.info("Execute trades to see P&L tracking.")

core.finalize_page()
