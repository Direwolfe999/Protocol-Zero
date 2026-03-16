from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

import app_core as core


core.render_shell(current_panel="🎙️  Voice AI", show_top_row=True)
flags = core.module_flags()
sonic = flags.get("nova_sonic")

st.markdown("### 🎙️ Nova Sonic — Voice AI War Room")
st.caption("Natural language voice commands & AI-generated alerts via Amazon Nova Sonic")

if not flags.get("has_nova_sonic") or sonic is None:
	st.warning("⚠️ Nova Sonic module not loaded. Ensure AWS credentials are configured.")
else:
	st.markdown("#### 💬 Send Command")
	vc_col1, vc_col2 = st.columns([4, 1])
	with vc_col1:
		voice_text = st.text_input(
			"Type a voice command",
			placeholder="What's my portfolio status? / Kill all trades / Buy 100 ETH",
			key="voice_text_input",
		)
	with vc_col2:
		st.markdown("<br>", unsafe_allow_html=True)
		voice_btn = st.button("🎤 Send", key="btn_voice_send", type="primary")

	if voice_btn and voice_text:
		with st.spinner("🎙️ Processing with Nova Sonic…"):
			core.cog("🎤", f"Voice command: {voice_text[:40]}…", "info")
			try:
				response = sonic.process_voice_text(
					voice_text,
					context={
						"portfolio_value": st.session_state.get("total_capital_usd", 10000),
						"session_pnl": st.session_state.get("session_pnl", 0),
						"trade_count": st.session_state.get("trade_count", 0),
						"kill_switch": st.session_state.get("kill_switch_active", False),
						"regime": st.session_state.get("market_regime", "UNCERTAIN"),
						"latest_decision": st.session_state.get("latest_decision"),
					},
				)

				entry = {
					"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
					"command": voice_text,
					"intent": getattr(response, "intent_handled", "unknown") if hasattr(response, "intent_handled") else response.get("intent_handled", "unknown"),
					"response_text": getattr(response, "text", str(response)) if hasattr(response, "text") else response.get("text", str(response)),
					"success": getattr(response, "success", True) if hasattr(response, "success") else response.get("success", True),
				}
				st.session_state["nova_voice_history"].append(entry)

				if entry["intent"] == "kill_switch":
					st.session_state["kill_switch_active"] = True
					st.session_state["autonomous_mode"] = False
					core.cog("⛔", "Voice command triggered KILL SWITCH", "err")

				core.cog("✓", f"Voice response: {entry['response_text'][:60]}…", "ok")
			except Exception as e:
				st.error(f"Voice processing failed: {e}")
				core.cog("✗", f"Nova Sonic error: {e}", "err")

	st.markdown("#### ⚡ Quick Voice Commands")
	qc1, qc2, qc3, qc4, qc5 = st.columns(5)
	quick_cmds = [
		(qc1, "📊 Status", "What's my portfolio status?"),
		(qc2, "⛔ Kill", "Kill all trades now"),
		(qc3, "📈 Risk", "What's the current risk level?"),
		(qc4, "💰 Balance", "Show my balance"),
		(qc5, "🧠 Regime", "What market regime are we in?"),
	]
	for col, label, cmd in quick_cmds:
		with col:
			if st.button(label, key=f"qcmd_{label}", use_container_width=True):
				try:
					resp = sonic.process_voice_text(cmd, context={"regime": st.session_state.get("market_regime", "UNCERTAIN")})
					st.session_state["nova_voice_history"].append(
						{
							"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
							"command": cmd,
							"intent": getattr(resp, "intent_handled", "unknown") if hasattr(resp, "intent_handled") else resp.get("intent_handled", "unknown"),
							"response_text": getattr(resp, "text", str(resp)) if hasattr(resp, "text") else resp.get("text", str(resp)),
							"success": True,
						}
					)
					if label == "⛔ Kill":
						st.session_state["kill_switch_active"] = True
						st.session_state["autonomous_mode"] = False
				except Exception as e:
					st.error(str(e))

	st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
	st.markdown("#### 🚨 AI Alert Generator")
	al_col1, al_col2 = st.columns([3, 1])
	with al_col1:
		alert_msg = st.text_input("Alert Message", placeholder="Sudden 15% price drop on ETH detected", key="alert_msg_input")
	with al_col2:
		alert_sev = st.selectbox("Severity", ["low", "medium", "high", "critical"], index=2, key="alert_severity")

	if st.button("🔊 Generate Alert", key="btn_gen_alert") and alert_msg:
		try:
			alert_resp = sonic.generate_alert(alert_sev, {"message": alert_msg})
			alert_text = getattr(alert_resp, "text", str(alert_resp)) if hasattr(alert_resp, "text") else alert_resp.get("text", str(alert_resp))
			st.session_state["nova_voice_history"].append(
				{
					"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
					"command": f"[ALERT:{alert_sev.upper()}] {alert_msg}",
					"intent": "alert",
					"response_text": alert_text,
					"success": True,
				}
			)
			core.cog("🚨", f"Alert generated: {alert_text[:60]}…", "err" if alert_sev in ("high", "critical") else "info")
		except Exception as e:
			st.error(str(e))

	st.markdown("#### 📜 Voice Command History")
	voice_hist = st.session_state.get("nova_voice_history", [])
	if voice_hist:
		for vh in reversed(voice_hist[-20:]):
			is_alert = vh.get("intent") == "alert"
			icon = "🚨" if is_alert else ("✅" if vh.get("success") else "❌")
			intent_color = "#ff6b6b" if is_alert else "#64ffda"
			st.markdown(
				f"""
				<div style="border-left:3px solid {intent_color};padding:0.6rem 0.8rem;
							margin:0.4rem 0;background:rgba(6,6,18,0.5);border-radius:0 8px 8px 0">
					<div style="display:flex;justify-content:space-between;align-items:center">
						<span style="font-size:0.85rem;color:#ccd6f6;font-weight:600">
							{icon} {vh['command'][:60]}{'…' if len(vh['command']) > 60 else ''}</span>
						<span style="color:#495670;font-size:0.65rem">{vh['timestamp']}</span>
					</div>
					<div style="color:#64ffda;font-size:0.7rem;margin-top:0.2rem">Intent: <b>{vh['intent']}</b></div>
					<div style="color:#8892b0;font-size:0.75rem;margin-top:0.3rem">{vh['response_text'][:200]}{'…' if len(vh.get('response_text', '')) > 200 else ''}</div>
				</div>
				""",
				unsafe_allow_html=True,
			)
	else:
		st.info("Type a voice command or use quick action buttons.")

if flags.get("has_nova_sonic") and sonic is not None:
	st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
	sonic_status = sonic.status()
	st.caption(
		f"Module: **Nova Sonic** · Mode: **{sonic_status.get('mode', 'unknown')}** · Commands Processed: **{len(st.session_state.get('nova_voice_history', []))}**"
	)

core.finalize_page()
