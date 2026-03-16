from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

import streamlit as st

import app_core as core


core.render_shell(current_panel="🎙️  Voice AI", show_top_row=True)
flags = core.module_flags()
sonic = flags.get("nova_sonic")

if "voice_session" not in st.session_state:
	st.session_state["voice_session"] = {
		"mode": "Push-to-Talk",
		"state": "idle",
		"listening": False,
		"speaking": False,
		"speaking_until": 0.0,
		"thinking": False,
		"last_response": "",
		"last_confidence": 0.5,
	}
if "voice_war_logs" not in st.session_state:
	st.session_state["voice_war_logs"] = []


def _log(event: str, **meta: Any) -> None:
	entry = {
		"ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
		"event": event,
		**meta,
	}
	st.session_state["voice_war_logs"].append(entry)
	if len(st.session_state["voice_war_logs"]) > 80:
		st.session_state["voice_war_logs"] = st.session_state["voice_war_logs"][-80:]


def _voice_context() -> dict:
	bal = core.refresh_wallet_balances(ttl_sec=12)
	eth_price = core.get_eth_usd_price_hint()
	return {
		"portfolio_value": st.session_state.get("total_capital_usd", 10000),
		"session_pnl": st.session_state.get("session_pnl", 0),
		"trade_count": st.session_state.get("trade_count", 0),
		"kill_switch": st.session_state.get("kill_switch_active", False),
		"regime": st.session_state.get("market_regime", "UNCERTAIN"),
		"market_regime": st.session_state.get("market_regime", "UNCERTAIN"),
		"reputation_score": st.session_state.get("reputation_score", 95),
		"latest_decision": st.session_state.get("latest_decision"),
		"wallet_eth": bal.get("wallet_eth", 0.0),
		"wallet_weth": bal.get("wallet_weth", 0.0),
		"wallet_usdc": bal.get("wallet_usdc", 0.0),
		"eth_price_usd": float(eth_price) if eth_price and eth_price > 0 else 0.0,
	}


def _confidence_from_intent(intent: str) -> float:
	intent = (intent or "").lower()
	if intent in {"kill_switch", "trade_confirm"}:
		return 0.9
	if intent in {"status", "risk_query", "balance"}:
		return 0.75
	if intent == "unknown":
		return 0.35
	return 0.6


def _speak_js(text: str) -> None:
	safe = text.replace("\\", "\\\\").replace("`", "\'")
	st.markdown(
		f"""
		<script>
		(function() {{
		  const txt = `{safe}`;
		  if (!txt) return;
		  const oldTitle = document.title;
		  document.title = "🔊 " + oldTitle.replace(/^🔊\s*/, "");
		  try {{
		    if ('speechSynthesis' in window) {{
		      const utter = new SpeechSynthesisUtterance(txt);
		      utter.rate = 1.0;
		      utter.pitch = 1.0;
		      utter.onend = () => {{ document.title = oldTitle.replace(/^🔊\s*/, ""); }};
		      window.speechSynthesis.cancel();
		      window.speechSynthesis.speak(utter);
		    }} else {{
		      document.title = oldTitle.replace(/^🔊\s*/, "");
		    }}
		  }} catch (_) {{ document.title = oldTitle.replace(/^🔊\s*/, ""); }}
		}})();
		</script>
		""",
		unsafe_allow_html=True,
	)


def _stream_chunks(gen: Iterator[str]) -> Iterator[str]:
	for chunk in gen:
		yield chunk
		time.sleep(0.01)


def _backup_stream_voice(command: str, context: dict, max_tokens: int = 140):
	bal = context.get("wallet_eth", 0.0)
	usdc = context.get("wallet_usdc", 0.0)
	eth_px = context.get("eth_price_usd", 0.0)
	text = (
		f"Backup Core engaged. Your current wallet shows approximately {bal:.4f} ETH and ${usdc:.2f} USDC. "
		f"ETH reference is ${eth_px:.2f}. Tactical systems remain operational in resilient mode."
	)

	def _gen() -> Iterator[str]:
		for tok in text.split(" "):
			yield tok + " "

	meta = {
		"tokens_per_sec": 11.0,
		"region": "local-resilience",
		"provider": "backup-core",
		"approx_tokens": len(text.split()),
	}
	return _gen(), meta


@core.protocol_zero_safe_run(retries=2, fallback_value=None, backup_bridge=_backup_stream_voice)
def _safe_stream_voice(command: str, context: dict, max_tokens: int = 140):
	return sonic.stream_voice_text(command, context=context, max_tokens=max_tokens)


def _process_command(command: str) -> None:
	if not command.strip():
		return
	t0 = time.perf_counter()
	ctx = _voice_context()
	st.session_state["voice_session"]["thinking"] = True
	st.session_state["voice_session"]["state"] = "thinking"
	st.session_state["voice_session"]["speaking"] = False
	core.cog("🎙️", f"War Room command: {command[:48]}", "info")
	try:
		stream_result = _safe_stream_voice(command, context=ctx, max_tokens=140)
		if not (isinstance(stream_result, tuple) and len(stream_result) == 2):
			stream_result = _backup_stream_voice(command, context=ctx, max_tokens=140)
		stream_gen, meta = stream_result
		st.markdown("#### 🧠 Streaming Response")
		st.session_state["voice_session"]["thinking"] = False
		st.session_state["voice_session"]["state"] = "speaking"
		response_text = st.write_stream(_stream_chunks(stream_gen))
		latency_ms = round((time.perf_counter() - t0) * 1000)
		intent = "unknown"
		try:
			intent = sonic._parse_command(command).intent  # best effort internal parse
		except Exception:
			pass
		conf = _confidence_from_intent(intent)

		entry = {
			"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
			"command": command,
			"intent": intent,
			"response_text": response_text,
			"success": True,
		}
		st.session_state["nova_voice_history"].append(entry)
		st.session_state["voice_session"]["last_response"] = response_text
		st.session_state["voice_session"]["last_confidence"] = conf

		if intent == "kill_switch":
			st.session_state["kill_switch_active"] = True
			st.session_state["autonomous_mode"] = False

		meta_line = {
			"latency_ms": latency_ms,
			"tokens_per_sec": meta.get("tokens_per_sec", 0.0),
			"region": meta.get("region", "us-west-2"),
			"provider": meta.get("provider", "nova"),
			"approx_tokens": meta.get("approx_tokens", 0),
		}
		_log("response", **meta_line)
		st.session_state["voice_session"]["speaking"] = True
		st.session_state["voice_session"]["speaking_until"] = time.time() + 4.0
		_speak_js(response_text)
	except Exception as e:
		st.error(f"Voice processing failed: {e}")
		_log("error", message=str(e))
	finally:
		st.session_state["voice_session"]["thinking"] = False
		if time.time() > float(st.session_state["voice_session"].get("speaking_until", 0.0)):
			st.session_state["voice_session"]["speaking"] = False
			st.session_state["voice_session"]["state"] = "idle"


st.markdown(
	"""
	<style>
	.voice-war-shell { border:1px solid rgba(79,195,247,.25); background:linear-gradient(180deg, rgba(12,12,31,.62), rgba(7,7,22,.45)); border-radius:14px; padding: .8rem .9rem; }
	.voice-wave-bars { height:48px; border-radius:10px; border:1px solid rgba(79,195,247,.25); background:#070716; position:relative; overflow:hidden; display:flex; align-items:flex-end; gap:6px; padding:8px; }
	.voice-wave-bars span { flex:1; border-radius:8px 8px 2px 2px; background:linear-gradient(180deg, rgba(100,255,218,.9), rgba(79,195,247,.45)); height:18%; opacity:.6; }
	.voice-wave-bars.idle span:nth-child(1){height:22%}.voice-wave-bars.idle span:nth-child(2){height:28%}.voice-wave-bars.idle span:nth-child(3){height:18%}.voice-wave-bars.idle span:nth-child(4){height:30%}
	.voice-wave-bars.idle span:nth-child(5){height:20%}.voice-wave-bars.idle span:nth-child(6){height:26%}.voice-wave-bars.idle span:nth-child(7){height:16%}.voice-wave-bars.idle span:nth-child(8){height:24%}
	.voice-wave-bars.listening span { animation: voiceBars 0.7s ease-in-out infinite; }
	.voice-wave-bars.thinking span { animation: voiceBars 1.0s ease-in-out infinite; }
	.voice-wave-bars.speaking span { animation: voiceBars 0.45s ease-in-out infinite; }
	.voice-wave-bars span:nth-child(2){animation-delay:.08s}.voice-wave-bars span:nth-child(3){animation-delay:.16s}.voice-wave-bars span:nth-child(4){animation-delay:.24s}
	.voice-wave-bars span:nth-child(5){animation-delay:.32s}.voice-wave-bars span:nth-child(6){animation-delay:.40s}.voice-wave-bars span:nth-child(7){animation-delay:.48s}.voice-wave-bars span:nth-child(8){animation-delay:.56s}
	.voice-wave-bars::after { content:""; position:absolute; inset:0; background:linear-gradient(90deg, transparent, rgba(100,255,218,.22), transparent); transform:translateX(-100%); }
	.voice-wave-bars.thinking::after, .voice-wave-bars.speaking::after { animation: voiceSweep 1.1s linear infinite; }
	@keyframes voiceSweep { to { transform:translateX(100%); } }
	@keyframes voiceBars { 0%,100% { height:18%; opacity:.45; } 50% { height:92%; opacity:1; } }
	.protocol-pulse { display:inline-block; width:11px; height:11px; border-radius:999px; margin-right:.45rem; }
	.protocol-pulse.green { background:#64ffda; box-shadow:0 0 0 rgba(100,255,218,.7); animation:pulseGreen 1.4s infinite; }
	.protocol-pulse.red { background:#ff6b6b; box-shadow:0 0 0 rgba(255,107,107,.7); animation:pulseRed 1.4s infinite; }
	@keyframes pulseGreen { 0% { box-shadow:0 0 0 0 rgba(100,255,218,.6);} 70% {box-shadow:0 0 0 10px rgba(100,255,218,0);} 100% {box-shadow:0 0 0 0 rgba(100,255,218,0);} }
	@keyframes pulseRed { 0% { box-shadow:0 0 0 0 rgba(255,107,107,.6);} 70% {box-shadow:0 0 0 10px rgba(255,107,107,0);} 100% {box-shadow:0 0 0 0 rgba(255,107,107,0);} }
	.war-log { max-height: 170px; overflow:auto; background:#060612; border:1px solid #1a1a3e; border-radius:10px; padding:.5rem .65rem; font-family:'JetBrains Mono', monospace; font-size:.72rem; }
	</style>
	""",
	unsafe_allow_html=True,
)

st.markdown("### 🎙️ Nova Sonic — Voice AI War Room")
st.caption("Realtime tactical voice interface · streaming responses · lightweight UI")

if not flags.get("has_nova_sonic") or sonic is None:
	st.warning("⚠️ Nova Sonic module not loaded. Ensure AWS credentials are configured.")
else:
	mode = st.radio("Input Mode", ["Push-to-Talk", "Auto-VAD"], horizontal=True, key="voice_mode")
	st.session_state["voice_session"]["mode"] = mode

	ptt_col, cmd_col = st.columns([1, 3])
	mic_text = ""
	audio_size = 0
	with ptt_col:
		try:
			from streamlit_mic_recorder import mic_recorder, speech_to_text  # type: ignore
			have_mic = True
		except Exception:
			have_mic = False

		if have_mic:
			if mode == "Auto-VAD":
				try:
					mic_text = speech_to_text(language="en", key="vad_stt", just_once=True) or ""
				except Exception:
					mic_text = ""
			else:
				audio = mic_recorder(start_prompt="🎤 Push to Talk", stop_prompt="⏹️ Stop", key="ptt_rec")
				if audio and isinstance(audio, dict):
					audio_size = len(audio.get("bytes", b""))
					if audio_size:
						_log("audio_buffer", bytes=audio_size)
		else:
			st.caption("Mic package missing. Install streamlit-mic-recorder.")

	with cmd_col:
		voice_text = st.text_input(
			"Voice Command",
			value=mic_text,
			placeholder="What's my portfolio status? / Kill all trades / Show my balance",
			key="voice_text_input",
		)
		st.session_state["voice_session"]["listening"] = bool(mic_text.strip()) and not st.session_state["voice_session"].get("thinking", False)

	if audio_size:
		st.caption(f"Audio buffer captured: {audio_size} bytes (routed for tactical processing)")

	send_col, quick_col = st.columns([1, 2])
	with send_col:
		send = st.button("⚡ Execute Voice Command", type="primary", use_container_width=True)
	with quick_col:
		q1, q2, q3, q4, q5 = st.columns(5)
		if q1.button("📊 Status", key="q_status", use_container_width=True):
			voice_text = "What's my portfolio status?"
			send = True
		if q2.button("⛔ Kill", key="q_kill", use_container_width=True):
			voice_text = "Kill all trades now"
			send = True
		if q3.button("📈 Risk", key="q_risk", use_container_width=True):
			voice_text = "What's the current risk level?"
			send = True
		if q4.button("💰 Balance", key="q_bal", use_container_width=True):
			voice_text = "Show my balance"
			send = True
		if q5.button("🧠 Regime", key="q_reg", use_container_width=True):
			voice_text = "What market regime are we in?"
			send = True

	if send and voice_text.strip():
		_process_command(voice_text)

	conf = float(st.session_state["voice_session"].get("last_confidence", 0.5))
	pulse = "green" if conf >= 0.6 else "red"
	now_ts = time.time()
	if now_ts > float(st.session_state["voice_session"].get("speaking_until", 0.0)):
		st.session_state["voice_session"]["speaking"] = False
	status = "idle"
	if st.session_state["voice_session"].get("thinking"):
		status = "thinking"
	elif st.session_state["voice_session"].get("speaking"):
		status = "speaking"
	elif st.session_state["voice_session"].get("listening"):
		status = "listening"
	st.session_state["voice_session"]["state"] = status
	bars = "".join(["<span></span>" for _ in range(8)])
	st.markdown(
		f"<div class='voice-war-shell'><div><span class='protocol-pulse {pulse}'></span><b>Protocol Pulse</b> · Confidence {conf:.0%}</div><div class='voice-wave-bars {status}'>{bars}</div></div>",
		unsafe_allow_html=True,
	)

	st.markdown("#### 🚨 AI Alert Generator")
	al_col1, al_col2 = st.columns([3, 1])
	with al_col1:
		alert_msg = st.text_input("Alert Message", placeholder="Sudden 15% price drop on ETH detected", key="alert_msg_input")
	with al_col2:
		alert_sev = st.selectbox("Severity", ["low", "medium", "high", "critical"], index=2, key="alert_severity")

	if st.button("🔊 Generate Alert", key="btn_gen_alert") and alert_msg:
		alert_resp = sonic.generate_alert(alert_sev, {"message": alert_msg})
		alert_text = getattr(alert_resp, "text", str(alert_resp)) if hasattr(alert_resp, "text") else str(alert_resp)
		st.session_state["nova_voice_history"].append(
			{
				"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
				"command": f"[ALERT:{alert_sev.upper()}] {alert_msg}",
				"intent": "alert",
				"response_text": alert_text,
				"success": True,
			}
		)
		_log("alert", severity=alert_sev, latency_ms=0)
		_speak_js(alert_text)

	st.markdown("#### 📜 Voice Command History")
	voice_hist = st.session_state.get("nova_voice_history", [])
	if voice_hist:
		for vh in reversed(voice_hist[-15:]):
			st.markdown(
				f"<div style='border-left:3px solid #64ffda;padding:.55rem .75rem;margin:.35rem 0;background:rgba(6,6,18,.5);border-radius:0 8px 8px 0'>"
				f"<div style='display:flex;justify-content:space-between'><b style='color:#ccd6f6'>{vh.get('command','')}</b><span style='color:#495670;font-size:.68rem'>{vh.get('timestamp','')}</span></div>"
				f"<div style='color:#8892b0;font-size:.78rem;margin-top:.2rem'>{str(vh.get('response_text',''))[:220]}</div>"
				f"</div>",
				unsafe_allow_html=True,
			)
	else:
		st.info("No voice commands yet.")

	st.markdown("#### 🖥️ Tactical Logging")
	logs = st.session_state.get("voice_war_logs", [])
	if logs:
		lines = [
			f"[{x.get('ts','--:--:--')}] {x.get('event','event')} | latency={x.get('latency_ms','-')}ms | tps={x.get('tokens_per_sec','-')} | region={x.get('region','us-west-2')} | provider={x.get('provider','nova')}"
			for x in logs[-25:]
		]
		st.markdown(f"<div class='war-log'>{'<br/>'.join(lines)}</div>", unsafe_allow_html=True)
	else:
		st.caption("Awaiting voice events…")

sonic_status = sonic.status() if flags.get("has_nova_sonic") and sonic is not None else {"mode": "offline"}
st.caption(
	f"Module: **Nova Sonic** · Mode: **{sonic_status.get('mode', 'unknown')}** · Voice Session Persisted: **Yes** · Commands: **{len(st.session_state.get('nova_voice_history', []))}**"
)

core.finalize_page()
