from __future__ import annotations

import numpy as np
import streamlit as st

import app_core as core


core.render_shell(current_panel="🔍  History", show_top_row=True)

st.markdown("### 🔍 AI Decision History")
st.caption("Full feed of AI decisions with profitability annotations")

history = st.session_state.get("decision_history", [])
if history:
	for dec in reversed(history):
		action = dec.get("action", "HOLD")
		conf = float(dec.get("confidence", 0))
		risk = int(dec.get("risk_score", 5))
		regime = dec.get("market_regime", "?")
		ts = dec.get("time", dec.get("timestamp", ""))
		reason = str(dec.get("entry_reasoning", dec.get("reasoning", "")))

		icon = {"BUY": "🟢", "SELL": "🔴"}.get(action, "🟡")
		css = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(action, "dec-hold")
		st.markdown(
			f"""
			<div class="dec-box {css}" style="padding:.8rem 1rem;margin:.4rem 0">
				<div style="display:flex;justify-content:space-between;align-items:center">
					<span style="font-size:1rem;font-weight:700">{icon} {action} {dec.get('asset', '?')}</span>
					<span style="color:#495670;font-size:.75rem">{ts}</span>
				</div>
				<div style="color:#8892b0;font-size:.78rem;margin-top:.3rem">
					Conf: <b>{conf:.0%}</b> · Risk: <b>{risk}/10</b> · Regime: <b>{regime}</b>
				</div>
				<div style="color:#495670;font-size:.72rem;margin-top:.2rem;font-style:italic">{reason[:140]}{'...' if len(reason) > 140 else ''}</div>
			</div>
			""",
			unsafe_allow_html=True,
		)

	buy = sum(1 for d in history if d.get("action") == "BUY")
	sell = sum(1 for d in history if d.get("action") == "SELL")
	hold = sum(1 for d in history if d.get("action") == "HOLD")
	avg_conf = float(np.mean([d.get("confidence", 0) for d in history])) if history else 0.0
	st.caption(
		f"Total: **{len(history)}** · 🟢 BUY: **{buy}** · 🔴 SELL: **{sell}** · 🟡 HOLD: **{hold}** · Avg Confidence: **{avg_conf:.0%}**"
	)
else:
	st.info("Run AI Analysis to build decision history.")

core.finalize_page()
