from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import plotly.graph_objects as go
import streamlit as st

import app_core as core


core.render_shell(current_panel="📊  Performance", show_top_row=True)

st.markdown("### 📊 Institutional Performance Analytics")
st.caption("Sharpe · Sortino · Calmar · Max Drawdown · Equity Curve")

perf = core.get_performance_report()

pm1, pm2, pm3, pm4, pm5, pm6 = st.columns(6)
with pm1:
	st.markdown(core.mcard("Sharpe Ratio", f"{perf.get('sharpe_ratio', 0.0):.2f}"), unsafe_allow_html=True)
with pm2:
	st.markdown(core.mcard("Sortino Ratio", f"{perf.get('sortino_ratio', 0.0):.2f}"), unsafe_allow_html=True)
with pm3:
	st.markdown(core.mcard("Calmar Ratio", f"{perf.get('calmar_ratio', 0.0):.2f}"), unsafe_allow_html=True)
with pm4:
	st.markdown(core.mcard("Max Drawdown", f"{perf.get('max_drawdown', 0.0):.1f}%"), unsafe_allow_html=True)
with pm5:
	st.markdown(core.mcard("Win Rate", f"{perf.get('win_rate', 0.0):.1f}%"), unsafe_allow_html=True)
with pm6:
	st.markdown(core.mcard("Profit Factor", f"{perf.get('profit_factor', 0.0):.2f}"), unsafe_allow_html=True)

st.markdown("#### 📈 Equity Curve")
tx_json = json.dumps(st.session_state.get("tx_log", []), default=str, sort_keys=True)
hist_json = json.dumps(st.session_state.get("decision_history", []), default=str, sort_keys=True)

equity = core.cached_equity_curve_from_txlog(tx_json, 10_000.0)
if len(equity) <= 1:
	equity = perf.get("equity_curve", []) or equity

if len(equity) > 1:
	fig_eq = go.Figure()
	fig_eq.add_trace(
		go.Scatter(
			y=equity,
			mode="lines",
			line=dict(color="#64ffda" if equity[-1] >= equity[0] else "#ff6b6b", width=2),
			fill="tozeroy",
			fillcolor="rgba(100,255,218,0.06)" if equity[-1] >= equity[0] else "rgba(255,107,107,0.06)",
		)
	)
	fig_eq.add_hline(y=equity[0], line_dash="dash", line_color="#495670", annotation_text="Starting Capital")
	fig_eq.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0,0,0,0)",
		plot_bgcolor="rgba(6,6,18,0.9)",
		height=300,
		margin=dict(l=0, r=0, t=10, b=0),
		yaxis=dict(gridcolor="#111130", title="Portfolio Value ($)"),
	)
	st.plotly_chart(fig_eq, use_container_width=True)
else:
	st.info("Execute trades to build the equity curve.")

st.markdown("#### 🎯 Performance by Market Regime")
regime_data = core.cached_regime_breakdown_from_logs(hist_json, tx_json)
if not regime_data:
	regime_data = perf.get("regime_breakdown", {})

if regime_data:
	regimes = list(regime_data.keys())
	wins = [regime_data[r].get("wins", 0) for r in regimes]
	losses = [regime_data[r].get("losses", 0) for r in regimes]
	fig_reg = go.Figure()
	fig_reg.add_trace(go.Bar(name="Wins", x=regimes, y=wins, marker_color="#64ffda"))
	fig_reg.add_trace(go.Bar(name="Losses", x=regimes, y=losses, marker_color="#ff6b6b"))
	fig_reg.update_layout(
		barmode="stack",
		template="plotly_dark",
		paper_bgcolor="rgba(0,0,0,0)",
		plot_bgcolor="rgba(6,6,18,0.9)",
		height=250,
		margin=dict(l=0, r=0, t=10, b=0),
	)
	st.plotly_chart(fig_reg, use_container_width=True)
else:
	st.info("Trade across different market regimes to see regime-specific performance.")

core.finalize_page()
