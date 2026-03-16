from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import app_core as core


core.render_shell(current_panel="🧠  Calibration", show_top_row=True)

st.markdown("### 🧠 AI Confidence Calibration")
st.caption("Predicted confidence vs realized outcomes")

cal_data = st.session_state.get("calibration_data", [])

if len(cal_data) >= 3:
	confs = [d["predicted_conf"] for d in cal_data]
	outcomes = [d["actual_outcome"] for d in cal_data]
	pnls = [d["pnl"] for d in cal_data]

	st.markdown("#### 📐 Calibration Curve")
	bins = [(0.0, 0.4), (0.4, 0.55), (0.55, 0.7), (0.7, 0.85), (0.85, 1.01)]
	labels = ["<40%", "40-55%", "55-70%", "70-85%", "85%+"]
	pred, actual = [], []
	for lo, hi in bins:
		bucket = [(c, o) for c, o in zip(confs, outcomes) if lo <= c < hi]
		if bucket:
			pred.append(np.mean([c for c, _ in bucket]) * 100)
			actual.append(np.mean([o for _, o in bucket]) * 100)
		else:
			pred.append((lo + hi) / 2 * 100)
			actual.append(0)

	fig = go.Figure()
	fig.add_trace(go.Scatter(x=list(range(len(labels))), y=pred, mode="lines+markers", name="Predicted", line=dict(color="#4fc3f7", width=2, dash="dash")))
	fig.add_trace(go.Scatter(x=list(range(len(labels))), y=actual, mode="lines+markers", name="Actual Win %", line=dict(color="#64ffda", width=3)))
	fig.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0,0,0,0)",
		plot_bgcolor="rgba(6,6,18,0.9)",
		height=300,
		margin=dict(l=0, r=0, t=10, b=0),
		xaxis=dict(ticktext=labels, tickvals=list(range(len(labels)))),
	)
	st.plotly_chart(fig, use_container_width=True)

	avg_conf = float(np.mean(confs) * 100)
	actual_wr = float(np.mean(outcomes) * 100)
	error = abs(avg_conf - actual_wr)

	cm1, cm2, cm3, cm4 = st.columns(4)
	with cm1:
		st.markdown(core.mcard("Avg Confidence", f"{avg_conf:.1f}%"), unsafe_allow_html=True)
	with cm2:
		st.markdown(core.mcard("Actual Win Rate", f"{actual_wr:.1f}%", up=actual_wr >= 50), unsafe_allow_html=True)
	with cm3:
		st.markdown(core.mcard("Calibration Error", f"{error:.1f}%"), unsafe_allow_html=True)
	with cm4:
		assessment = "Well Calibrated" if error < 10 else "Needs Tuning"
		st.markdown(core.mcard("Assessment", assessment), unsafe_allow_html=True)

	st.markdown("#### 💰 Confidence vs PnL")
	colors = ["#64ffda" if p > 0 else "#ff6b6b" for p in pnls]
	fig_sc = go.Figure(
		go.Scatter(
			x=[c * 100 for c in confs],
			y=pnls,
			mode="markers",
			marker=dict(size=10, color=colors, line=dict(width=1, color="#1a1a3e")),
		)
	)
	fig_sc.add_hline(y=0, line_dash="dash", line_color="#495670")
	fig_sc.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=250, margin=dict(l=0, r=0, t=10, b=0))
	st.plotly_chart(fig_sc, use_container_width=True)
else:
	st.info(f"Execute at least {3 - len(cal_data)} more trade(s) to see calibration analytics.")

core.finalize_page()
