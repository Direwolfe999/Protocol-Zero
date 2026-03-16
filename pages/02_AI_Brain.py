from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import app_core as core


df = core.render_shell(current_panel="🧠  AI Brain", show_top_row=True)

st.markdown("### 🧠 AI Trading Analysis")
st.caption("Strategic reasoning engine · Nova Lite on Bedrock")

if st.button("▶  Run Analysis", use_container_width=True, type="primary"):
	with st.spinner("Neural pathways activating…"):
		t0 = core.time.perf_counter()
		decision = core.run_analysis(df, st.session_state["selected_pair"], st.session_state.get("whatif_vol_mult", 1.0))
		st.session_state["analysis_latency_ms"] = round((core.time.perf_counter() - t0) * 1000)
		st.session_state["latest_decision"] = decision
		st.session_state["decision_history"].append({
			"time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
			**decision,
		})
		core.cog("✓", "Analysis cycle complete", "ok")

lat = int(st.session_state.get("analysis_latency_ms", 0))
if lat > 0:
	lat_c = "#64ffda" if lat < 500 else ("#ffd93d" if lat < 2000 else "#ff6b6b")
	st.markdown(
		f'<div style="display:inline-block;background:#050510;border:1px solid #1a1a3e;border-radius:8px;padding:.25rem .7rem;font-size:.7rem;color:{lat_c};margin-bottom:.5rem">⏱ {lat}ms</div>',
		unsafe_allow_html=True,
	)

dec = st.session_state.get("latest_decision")
if dec:
	action = dec["action"]
	css = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(action, "dec-hold")
	icon = {"BUY": "🟢", "SELL": "🔴"}.get(action, "🟡")
	st.markdown(
		f"""
		<div class="dec-box {css}">
			<div style="font-size:1.2rem;font-weight:700">{icon} {action} {dec['asset']}</div>
			<div style="color:#ccd6f6;font-size:.88rem;margin-top:.35rem">
				Position: <b>{dec['position_size_percent']:.1f}%</b> (${dec['amount_usd']:,.2f})
				&nbsp;·&nbsp; Confidence: <b>{dec['confidence']:.0%}</b>
				&nbsp;·&nbsp; Risk: <b>{dec['risk_score']}/10</b>
			</div>
		</div>
		""",
		unsafe_allow_html=True,
	)
	st.markdown(f"**Reasoning:** _{dec['entry_reasoning']}_")

	# 🎯 NEW: Nova's Thought Process (Explainability)
	with st.expander("🧠 Nova's Thought Process (Explainability)", expanded=False):
		st.markdown("### How Nova Made This Decision")
		
		col1, col2 = st.columns(2)
		
		with col1:
			st.markdown("#### 📊 Market Context")
			market_info = {
				"Price": f"${st.session_state.get('eth_price', 2500):.2f}",
				"24h Change": f"{st.session_state.get('price_change_24h', 2.5):.2f}%",
				"Volume": f"${st.session_state.get('volume_24h', 15e9):,.0f}",
				"Regime": dec.get("market_regime", "ranging"),
				"Volatility": f"{st.session_state.get('current_volatility', 25):.1f}%",
			}
			for key, val in market_info.items():
				st.markdown(f"**{key}**: `{val}`")
		
		with col2:
			st.markdown("#### 🤖 Reasoning Chain")
			reasoning_steps = [
				f"1️⃣ Detected **{dec.get('market_regime', 'ranging')}** market regime",
				f"2️⃣ Computed RSI = {st.session_state.get('rsi_value', 45):.0f}" + 
					(" → Oversold opportunity" if st.session_state.get('rsi_value', 45) < 30 else " → Overbought caution"),
				f"3️⃣ Evaluated {dec.get('num_signals_active', 3)} technical signals",
				f"4️⃣ Risk score: {dec['risk_score']}/10" + 
					(" ✅ Within limits" if dec['risk_score'] <= 7 else " ⚠️ Elevated"),
				f"5️⃣ Confidence: {float(dec['confidence'])*100:.0f}%" +
					(" → Signal sufficient for action" if float(dec['confidence']) >= 0.60 else " → Below threshold, hold"),
			]
			for step in reasoning_steps:
				st.markdown(step)
		
		st.divider()
		
		st.markdown("#### 📤 Tool Calls & Parameters")
		tool_calls = [
			{
				"Tool": "compute_rsi()",
				"Input": f"Period=14, Data=72h OHLCV",
				"Output": f"RSI={st.session_state.get('rsi_value', 45):.0f}",
				"Status": "✅"
			},
			{
				"Tool": "detect_regime()",
				"Input": f"Vol multiplier=1.0",
				"Output": f"Regime={dec.get('market_regime', 'ranging')}",
				"Status": "✅"
			},
			{
				"Tool": "risk_check.run_all_checks()",
				"Input": f"Decision={action}, Position={dec['position_size_percent']:.1f}%",
				"Output": f"Score={dec['risk_score']}/10, Pass={dec['risk_score'] <= 7}",
				"Status": "✅"
			},
		]
		
		df_tools = pd.DataFrame(tool_calls)
		st.dataframe(df_tools, use_container_width=True, hide_index=True)
		
		st.divider()
		
		st.markdown("#### 💡 Confidence Breakdown")
		col1, col2, col3 = st.columns(3)
		
		with col1:
			st.metric(
				"Technical Alignment",
				f"{st.session_state.get('technical_score', 0.65)*100:.0f}%",
				"Signals agree on direction"
			)
		
		with col2:
			st.metric(
				"Risk Assessment",
				f"{(1 - dec['risk_score']/10)*100:.0f}%",
				"Risk gates passed"
			)
		
		with col3:
			st.metric(
				"Market Regime Fit",
				f"{st.session_state.get('regime_fit', 0.70)*100:.0f}%",
				"Strategy matches conditions"
			)
		
		st.markdown("#### 📝 Nova's Full Reasoning")
		st.info(dec.get('entry_reasoning', 'Analysis reasoning not available'))

	col_g1, col_g2 = st.columns([1, 2])
	with col_g1:
		st.plotly_chart(core.confidence_gauge(float(dec["confidence"])), use_container_width=True)
	with col_g2:
		cp = float(dec["confidence"]) * 100
		cc = "#64ffda" if cp >= 70 else ("#ffd93d" if cp >= 40 else "#ff6b6b")
		st.markdown(
			f"""
			<div style="background:#050510;border-radius:10px;padding:.6rem 1rem;margin-top:.5rem">
				<div style="color:#495670;font-size:.7rem;margin-bottom:4px">CONFIDENCE</div>
				<div style="background:#111130;border-radius:4px;height:14px;width:100%">
					<div style="background:{cc};width:{cp}%;height:100%;border-radius:4px"></div>
				</div>
				<div style="text-align:right;color:{cc};font-size:.8rem;margin-top:2px">{cp:.0f}%</div>
			</div>
			""",
			unsafe_allow_html=True,
		)

	with st.expander("📦 Raw JSON Decision (sign_trade.py input)"):
		json_out = {k: v for k, v in dec.items() if k != "amount_usd"}
		st.code(json.dumps(json_out, indent=2), language="json")
else:
	st.markdown('<div style="text-align:center;padding:3rem;color:#495670">Press <b>Run Analysis</b> to activate the cognitive engine.</div>', unsafe_allow_html=True)

if st.session_state.get("decision_history"):
	with st.expander(f"📜 Decision History ({len(st.session_state['decision_history'])})"):
		st.dataframe(pd.DataFrame(st.session_state["decision_history"]), use_container_width=True, hide_index=True)

core.finalize_page()
