from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import app_core as core


df = core.render_shell(current_panel="📊  Market", show_top_row=True)

pair = str(st.session_state.get("selected_pair", "ETH/USDT"))

col_pair, col_ref, col_live = st.columns([2.2, 0.9, 1.5])
with col_pair:
	new_pair = st.selectbox(
		"Trading Pair",
		list(core._BASE_PRICES.keys()),
		index=(list(core._BASE_PRICES.keys()).index(pair) if pair in core._BASE_PRICES else 0),
		key="pair_sel",
	)
	if new_pair != st.session_state["selected_pair"]:
		st.session_state["selected_pair"] = new_pair
		core.load_market_data(new_pair)
		st.session_state["_last_market_refresh"] = core.time.time()
		df = st.session_state["market_df"]
with col_ref:
	st.markdown("<br>", unsafe_allow_html=True)
	if st.button("🔄 Refresh", use_container_width=True):
		df = core.load_market_data(st.session_state["selected_pair"])
		st.session_state["_last_market_refresh"] = core.time.time()
with col_live:
	st.session_state["market_live_refresh"] = st.toggle(
		"Live Price",
		value=bool(st.session_state.get("market_live_refresh", False)),
		key="market_live_toggle",
	)
	st.session_state["market_refresh_sec"] = st.select_slider(
		"Refresh",
		options=[10, 15, 30, 60],
		value=int(st.session_state.get("market_refresh_sec", 15)),
		key="market_refresh_slider",
	)

latest = df["close"].iloc[-1]
prev = df["close"].iloc[-2]
change = ((latest - prev) / prev) * 100
vol24 = df["volume"].tail(24).sum()
h24 = df["high"].tail(24).max()
l24 = df["low"].tail(24).min()
rsi_now = df["rsi_14"].iloc[-1] if df["rsi_14"].notna().iloc[-1] else 50.0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
	st.markdown(core.mcard("Price", f"${latest:,.2f}", f"{change:+.2f}%", change >= 0), unsafe_allow_html=True)
with c2:
	st.markdown(core.mcard("24h High", f"${h24:,.2f}"), unsafe_allow_html=True)
with c3:
	st.markdown(core.mcard("24h Low", f"${l24:,.2f}"), unsafe_allow_html=True)
with c4:
	st.markdown(core.mcard("24h Volume", f"{vol24:,.0f}"), unsafe_allow_html=True)
with c5:
	rl = "Oversold" if rsi_now < 30 else ("Overbought" if rsi_now > 70 else "Neutral")
	st.markdown(core.mcard("RSI-14", f"{rsi_now:.1f}", rl, 30 < rsi_now < 70), unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(
	go.Candlestick(
		x=df["timestamp"],
		open=df["open"],
		high=df["high"],
		low=df["low"],
		close=df["close"],
		name="OHLC",
		increasing_line_color="#64ffda",
		decreasing_line_color="#ff6b6b",
	)
)
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["sma_12"], name="SMA-12", line=dict(color="#4fc3f7", width=1.5, dash="dot")))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["sma_26"], name="SMA-26", line=dict(color="#ffd93d", width=1.5, dash="dot")))
fig.update_layout(
	template="plotly_dark",
	paper_bgcolor="rgba(0,0,0,0)",
	plot_bgcolor="rgba(6,6,18,0.9)",
	height=400,
	margin=dict(l=0, r=0, t=10, b=0),
	xaxis_rangeslider_visible=False,
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("📊 Volume Profile"):
	colors = ["#64ffda" if df["close"].iloc[i] >= df["open"].iloc[i] else "#ff6b6b" for i in range(len(df))]
	fig_v = go.Figure(go.Bar(x=df["timestamp"], y=df["volume"], marker_color=colors))
	fig_v.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0,0,0,0)",
		plot_bgcolor="rgba(6,6,18,0.9)",
		height=180,
		margin=dict(l=0, r=0, t=10, b=0),
	)
	st.plotly_chart(fig_v, use_container_width=True)

core.finalize_page()
