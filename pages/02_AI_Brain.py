from __future__ import annotations

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
