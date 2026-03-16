from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import app_core as core


mdf = core.render_shell(current_panel="📡  Microstructure", show_top_row=True)

st.markdown("### 📡 Live Market Microstructure")
st.caption("Volatility regimes · Volume profile · Regime transitions")

if mdf is not None and len(mdf) > 10:
	st.markdown("#### 📊 Volatility Term Structure")
	windows = [5, 10, 20, 40]
	vals = []
	for w in windows:
		v = mdf["pct_change"].rolling(w).std().iloc[-1]
		vals.append(float(v) if pd.notna(v) else 0)

	fig_vol = go.Figure(go.Bar(
		x=[f"{w}h" for w in windows],
		y=vals,
		marker_color=["#64ffda" if v < 0.8 else ("#ffd93d" if v < 1.5 else "#ff6b6b") for v in vals],
		text=[f"{v:.3f}" for v in vals],
		textposition="outside",
	))
	fig_vol.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=250, margin=dict(l=0, r=0, t=10, b=0))
	st.plotly_chart(fig_vol, use_container_width=True)

	st.markdown("#### 🔥 Volume Profile Heatmap")
	pmin, pmax = mdf["low"].min(), mdf["high"].max()
	n_bins = 20
	edges = np.linspace(pmin, pmax, n_bins + 1)
	profile = np.zeros(n_bins)
	for _, row in mdf.iterrows():
		for j in range(n_bins):
			if row["low"] <= edges[j + 1] and row["high"] >= edges[j]:
				profile[j] += row["volume"]
	labels = [f"${(edges[i] + edges[i + 1]) / 2:,.0f}" for i in range(n_bins)]
	fig_vp = go.Figure(go.Bar(y=labels, x=profile, orientation="h"))
	fig_vp.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=380, margin=dict(l=0, r=0, t=10, b=0))
	st.plotly_chart(fig_vp, use_container_width=True)

	st.markdown("#### 🔄 Regime Transition Analysis")
	regimes_series = []
	for i in range(26, len(mdf)):
		regimes_series.append(core.detect_regime(mdf.iloc[: i + 1].copy(), 1.0))
	if len(regimes_series) > 2:
		names = ["TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"]
		trans = {r1: {r2: 0 for r2 in names} for r1 in names}
		for i in range(1, len(regimes_series)):
			trans[regimes_series[i - 1]][regimes_series[i]] += 1
		z = [[trans[r1][r2] for r2 in names] for r1 in names]
		fig_t = go.Figure(go.Heatmap(z=z, x=names, y=names, colorscale=[[0, "#060612"], [0.5, "#4fc3f7"], [1, "#64ffda"]]))
		fig_t.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=300, margin=dict(l=0, r=0, t=10, b=0))
		st.plotly_chart(fig_t, use_container_width=True)

	st.markdown("#### 📊 Return Distribution")
	returns = mdf["pct_change"].dropna().values
	if len(returns) > 5:
		fig_d = go.Figure(go.Histogram(x=returns, nbinsx=30, marker_color="#4fc3f7", opacity=0.7))
		fig_d.add_vline(x=0, line_dash="dash", line_color="#ffd93d")
		fig_d.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,6,18,0.9)", height=250, margin=dict(l=0, r=0, t=10, b=0))
		st.plotly_chart(fig_d, use_container_width=True)
else:
	st.info("Load market data to see microstructure analysis.")

core.finalize_page()
