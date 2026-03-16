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
	
	# Show premium thinking indicator
	thinking_placeholder = st.empty()
	with thinking_placeholder.container():
		st.markdown(core.render_voice_thinking(), unsafe_allow_html=True)
	st.session_state["voice_session"]["speaking"] = False
	core.cog("🎙️", f"War Room command: {command[:48]}", "info")
	try:
		stream_result = _safe_stream_voice(command, context=ctx, max_tokens=140)
		if not (isinstance(stream_result, tuple) and len(stream_result) == 2):
			stream_result = _backup_stream_voice(command, context=ctx, max_tokens=140)
		stream_gen, meta = stream_result
		thinking_placeholder.empty()  # Clear thinking indicator
		st.markdown("#### 🧠 Streaming Response")
		st.session_state["voice_session"]["thinking"] = False
		st.session_state["voice_session"]["state"] = "speaking"
		
		# Show futuristic waveform while speaking
		st.markdown(core.render_voice_waveform(12), unsafe_allow_html=True)
		
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
			"confidence": conf,
			"latency_ms": latency_ms,
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
	.voice-page-title { margin-bottom: .35rem; letter-spacing:.2px; }
	.voice-page-subtitle { color:#94a3b8; margin-bottom: 1rem; }
	.voice-bento-grid { display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:.85rem; margin-bottom:.65rem; }
	.voice-bento-card { border:1px solid rgba(79,195,247,.18); background:linear-gradient(180deg, rgba(12,12,31,.76), rgba(8,8,24,.66)); border-radius:14px; padding:.9rem .95rem; box-shadow:0 10px 28px rgba(0,0,0,.24); position:relative; overflow:hidden; }
	.voice-bento-card::before {
		content:"";
		position:absolute;
		inset:0;
		background:radial-gradient(85% 65% at 102% -10%, rgba(244,114,182,.12), transparent 45%), radial-gradient(70% 55% at -8% 105%, rgba(56,189,248,.12), transparent 48%);
		pointer-events:none;
	}
	.voice-bento-card::after {
		content:"";
		position:absolute;
		left:0;
		right:0;
		top:0;
		height:1px;
		background:linear-gradient(90deg, transparent, rgba(250,204,21,.42), rgba(167,139,250,.35), transparent);
		pointer-events:none;
	}
	.voice-bento-card--hero { grid-column:span 12; padding:1rem 1.05rem; border-color:rgba(100,255,218,.28); }
	.voice-bento-card--main { grid-column:span 8; }
	.voice-bento-card--side { grid-column:span 4; }
	.voice-bento-card h4 { margin:.1rem 0 .6rem 0; color:#dbeafe; font-size:.95rem; letter-spacing:.2px; }
	.voice-chip-row { display:flex; gap:.45rem; flex-wrap:wrap; margin-top:.4rem; }
	.voice-chip { border:1px solid rgba(148,163,184,.25); border-radius:999px; padding:.2rem .55rem; font-size:.72rem; color:#bfdbfe; background:rgba(15,23,42,.55); }
	.voice-chip.ok { border-color:rgba(100,255,218,.45); color:#99f6e4; }
	.voice-chip.warn { border-color:rgba(248,113,113,.42); color:#fecaca; }
	.voice-bento-card--hero .voice-chip.ok { border-color:rgba(250,204,21,.55); color:#fde68a; background:rgba(54,40,7,.36); }
	.voice-war-shell { border:1px solid rgba(79,195,247,.25); background:linear-gradient(180deg, rgba(12,12,31,.62), rgba(7,7,22,.45)); border-radius:12px; padding: .75rem .82rem; }
	.voice-wave-bars { height:48px; border-radius:10px; border:1px solid rgba(79,195,247,.25); background:#070716; position:relative; overflow:hidden; display:flex; align-items:flex-end; gap:6px; padding:8px; margin-top:.4rem; }
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
	.war-log { max-height: 220px; overflow:auto; background:#060612; border:1px solid #1a1a3e; border-radius:10px; padding:.55rem .7rem; font-family:'JetBrains Mono', monospace; font-size:.72rem; }
	.voice-history-item { border-left:3px solid #64ffda; padding:.55rem .75rem; margin:.42rem 0; background:rgba(6,6,18,.56); border-radius:0 8px 8px 0; }
	div[data-testid="stRadio"] > div { padding:.18rem .2rem .08rem .2rem; background:rgba(15,23,42,.35); border:1px solid rgba(79,195,247,.2); border-radius:10px; }
	div[data-testid="stTextInput"] > div > div { border-radius:10px; }
	div[data-testid="stButton"] button { border-radius:10px; font-weight:600; }
	.voice-exec-btn { 
		background:linear-gradient(120deg, #0ea5e9, #2563eb 40%, #7c3aed 72%, #ec4899) !important;
		border:1px solid rgba(244,208,63,.55) !important;
		color:#eff6ff !important;
		box-shadow:0 10px 24px rgba(37,99,235,.34), 0 0 0 1px rgba(244,208,63,.26), inset 0 1px 0 rgba(255,255,255,.22);
		letter-spacing:.2px;
		position:relative;
		overflow:hidden;
		text-shadow:0 1px 10px rgba(7,18,42,.45);
	}
	.voice-exec-btn::after {
		content:"";
		position:absolute;
		inset:0;
		background:linear-gradient(105deg, transparent 20%, rgba(255,255,255,.35) 48%, transparent 70%);
		transform:translateX(-130%);
		transition:transform .55s ease;
	}
	.voice-exec-btn:hover::after { transform:translateX(130%); }
	.voice-exec-btn:hover { transform:translateY(-1px); filter:brightness(1.05); box-shadow:0 14px 28px rgba(37,99,235,.42), 0 0 20px rgba(250,204,21,.22), inset 0 1px 0 rgba(255,255,255,.28); }
	.voice-quick-btn {
		background:linear-gradient(180deg, rgba(15,23,42,.96), rgba(8,14,28,.92)) !important;
		border:1px solid rgba(100,116,139,.45) !important;
		color:#cbd5e1 !important;
		box-shadow:0 8px 18px rgba(2,6,23,.42), inset 0 1px 0 rgba(255,255,255,.06);
		transition:all .18s ease !important;
		font-weight:700 !important;
		letter-spacing:.18px;
		position:relative;
		overflow:hidden;
	}
	.voice-quick-btn::before {
		content:"";
		position:absolute;
		inset:-1px;
		background:linear-gradient(115deg, rgba(148,163,184,.16), rgba(94,234,212,.12), rgba(250,204,21,.14));
		opacity:.55;
		pointer-events:none;
	}
	.voice-quick-btn::after {
		content:"";
		position:absolute;
		inset:0;
		background:linear-gradient(110deg, transparent 24%, rgba(255,255,255,.2) 48%, transparent 70%);
		transform:translateX(-130%);
		transition:transform .42s ease;
		pointer-events:none;
	}
	.voice-quick-btn:hover {
		border-color:rgba(94,234,212,.6) !important;
		color:#ecfeff !important;
		transform:translateY(-1px) scale(1.01);
		box-shadow:0 12px 24px rgba(8,145,178,.23), inset 0 1px 0 rgba(255,255,255,.16);
	}
	.voice-quick-btn:hover::after { transform:translateX(130%); }
	.voice-quick-btn[data-voice-tone="kill"] {
		border-color:rgba(248,113,113,.58) !important;
		color:#fecaca !important;
		background:linear-gradient(180deg, rgba(39,12,22,.95), rgba(26,7,14,.92)) !important;
	}
	.voice-quick-btn[data-voice-tone="kill"]::before {
		background:linear-gradient(115deg, rgba(254,202,202,.14), rgba(248,113,113,.18), rgba(185,28,28,.22));
	}
	.voice-quick-btn[data-voice-tone="kill"]:hover {
		border-color:rgba(252,165,165,.8) !important;
		box-shadow:0 12px 24px rgba(239,68,68,.25), inset 0 1px 0 rgba(255,255,255,.12);
	}
	@media (max-width: 1100px) {
		.voice-bento-card--main, .voice-bento-card--side { grid-column:span 12; }
	}
	@media (max-width: 780px) {
		.voice-bento-grid { gap:.65rem; }
		.voice-bento-card { padding:.8rem .8rem; }
		.voice-page-subtitle { margin-bottom:.75rem; }
	}
	</style>
	""",
	unsafe_allow_html=True,
)

st.markdown("<h3 class='voice-page-title'>🎙️ Nova Sonic — Voice AI War Room</h3>", unsafe_allow_html=True)
st.markdown("<div class='voice-page-subtitle'>Realtime tactical voice interface · streaming responses · polished command workflow</div>", unsafe_allow_html=True)

if not flags.get("has_nova_sonic") or sonic is None:
	st.warning("⚠️ Nova Sonic module not loaded. Ensure AWS credentials are configured.")
else:
	commands_count = len(st.session_state.get("nova_voice_history", []))
	kill_state = bool(st.session_state.get("kill_switch_active", False))
	regime = st.session_state.get("market_regime", "UNCERTAIN")
	st.markdown(
		"<div class='voice-bento-grid'><div class='voice-bento-card voice-bento-card--hero'>"
		"<h4>Mission Control Snapshot</h4>"
		f"<div class='voice-chip-row'>"
		f"<span class='voice-chip ok'>Nova Sonic Online</span>"
		f"<span class='voice-chip'>{regime}</span>"
		f"<span class='voice-chip'>Commands {commands_count}</span>"
		f"<span class='voice-chip {'warn' if kill_state else 'ok'}'>{'Kill-Switch Active' if kill_state else 'Kill-Switch Clear'}</span>"
		"</div>"
		"</div></div>",
		unsafe_allow_html=True,
	)

	st.markdown("<div class='voice-bento-grid'>", unsafe_allow_html=True)
	st.markdown("<div class='voice-bento-card voice-bento-card--main'><h4>Command Console</h4>", unsafe_allow_html=True)
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
	st.markdown(
		"""
		<script>
		(function() {
		  const allButtons = Array.from(window.parent.document.querySelectorAll('button'));
		  const buttons = allButtons.filter((btn) => {
		    const text = (btn.innerText || '').trim().toLowerCase();
		    return (
		      text.includes('execute voice command') ||
		      text.includes('status') ||
		      text.includes('kill') ||
		      text.includes('risk') ||
		      text.includes('balance') ||
		      text.includes('regime')
		    );
		  });
		  const quickMap = [
		    { t: 'status', tone: 'normal' },
		    { t: 'kill', tone: 'kill' },
		    { t: 'risk', tone: 'normal' },
		    { t: 'balance', tone: 'normal' },
		    { t: 'regime', tone: 'normal' }
		  ];
		  buttons.forEach((btn) => {
		    const text = (btn.innerText || '').trim().toLowerCase();
		    if (!text) return;
		    if (text.includes('execute voice command')) {
		      btn.classList.add('voice-exec-btn');
		    }
		    for (const item of quickMap) {
		      if (text.includes(item.t)) {
		        btn.classList.add('voice-quick-btn');
		        btn.setAttribute('data-voice-tone', item.tone);
		      }
		    }
		  });
		})();
		</script>
		""",
		unsafe_allow_html=True,
	)
	
	# Add keyboard shortcuts listener
	st.markdown("""
	<script>
	(function() {
		document.addEventListener('keydown', function(e) {
			// Only trigger if not in text input
			if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
			
			if (e.altKey && !e.ctrlKey && !e.metaKey) {
				const key = e.key.toLowerCase();
				let action = null;
				
				if (key === 'v') {
					// Alt+V: Push-to-Talk
					action = 'ptt_rec';
				} else if (key === 'k') {
					// Alt+K: Kill Switch
					action = 'q_kill';
				} else if (key === 's') {
					// Alt+S: Status
					action = 'q_status';
				} else if (key === 'r') {
					// Alt+R: Risk
					action = 'q_risk';
				}
				
				if (action) {
					e.preventDefault();
					const btn = document.querySelector(`[data-testid*="stButton"][data-test-key="${action}"], button[data-key="${action}"]`);
					if (btn) {
						btn.click();
					} else {
						// Try to find by text content
						const allBtn = Array.from(document.querySelectorAll('button'));
						let target = null;
						if (action === 'q_kill') target = allBtn.find(b => b.innerText.includes('Kill'));
						else if (action === 'q_status') target = allBtn.find(b => b.innerText.includes('Status'));
						else if (action === 'q_risk') target = allBtn.find(b => b.innerText.includes('Risk'));
						
						if (target) target.click();
					}
				}
			}
		});
	})();
	</script>
	""", unsafe_allow_html=True)
	
	st.markdown("</div>", unsafe_allow_html=True)

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
	st.markdown("<div class='voice-bento-card voice-bento-card--side'><h4>Voice Signal</h4>", unsafe_allow_html=True)
	st.markdown(
		f"<div class='voice-war-shell'><div><span class='protocol-pulse {pulse}'></span><b>Protocol Pulse</b> · Confidence {conf:.0%}</div><div class='voice-wave-bars {status}'>{bars}</div></div>",
		unsafe_allow_html=True,
	)
	st.markdown("</div></div>", unsafe_allow_html=True)

	st.markdown("<div class='voice-bento-grid'><div class='voice-bento-card voice-bento-card--main'><h4>🚨 AI Alert Generator</h4>", unsafe_allow_html=True)
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
	st.markdown("</div>", unsafe_allow_html=True)

	st.markdown("<div class='voice-bento-card voice-bento-card--side'><h4>🖥️ Tactical Logging</h4>", unsafe_allow_html=True)
	logs = st.session_state.get("voice_war_logs", [])
	if logs:
		lines = [
			f"[{x.get('ts','--:--:--')}] {x.get('event','event')} | latency={x.get('latency_ms','-')}ms | tps={x.get('tokens_per_sec','-')} | region={x.get('region','us-west-2')} | provider={x.get('provider','nova')}"
			for x in logs[-25:]
		]
		st.markdown(f"<div class='war-log'>{'<br/>'.join(lines)}</div>", unsafe_allow_html=True)
	else:
		st.caption("Awaiting voice events…")
	st.markdown("</div></div>", unsafe_allow_html=True)

	st.markdown("<div class='voice-bento-grid'><div class='voice-bento-card voice-bento-card--hero'><h4>📜 Voice Command History</h4>", unsafe_allow_html=True)
	voice_hist = st.session_state.get("nova_voice_history", [])
	if voice_hist:
		for vh in reversed(voice_hist[-15:]):
			st.markdown(
				f"<div class='voice-history-item'>"
				f"<div style='display:flex;justify-content:space-between'><b style='color:#ccd6f6'>{vh.get('command','')}</b><span style='color:#495670;font-size:.68rem'>{vh.get('timestamp','')}</span></div>"
				f"<div style='color:#8892b0;font-size:.78rem;margin-top:.2rem'>{str(vh.get('response_text',''))[:220]}</div>"
				f"</div>",
				unsafe_allow_html=True,
			)
	else:
		st.info("No voice commands yet.")
	st.markdown("</div></div>", unsafe_allow_html=True)

sonic_status = sonic.status() if flags.get("has_nova_sonic") and sonic is not None else {"mode": "offline"}

# Display keyboard shortcuts
st.markdown("""
<div style="background:linear-gradient(135deg,rgba(79,195,247,.05),rgba(100,255,218,.02));border:1px solid rgba(100,255,218,.2);border-radius:12px;padding:1rem;margin:1rem 0">
    <div style="font-weight:700;color:#64ffda;margin-bottom:0.8rem;font-size:0.9rem;text-transform:uppercase;letter-spacing:1px">⌨️ Keyboard Shortcuts</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;font-size:0.82rem;color:#9eeeff">
        <div><kbd style="background:#111130;border:1px solid #1a1a3e;padding:0.3rem 0.6rem;border-radius:4px;font-family:monospace;color:#64ffda">Alt+V</kbd> Push-to-Talk</div>
        <div><kbd style="background:#111130;border:1px solid #1a1a3e;padding:0.3rem 0.6rem;border-radius:4px;font-family:monospace;color:#ff6b6b">Alt+K</kbd> Kill Switch</div>
        <div><kbd style="background:#111130;border:1px solid #1a1a3e;padding:0.3rem 0.6rem;border-radius:4px;font-family:monospace;color:#64ffda">Alt+S</kbd> Status Check</div>
        <div><kbd style="background:#111130;border:1px solid #1a1a3e;padding:0.3rem 0.6rem;border-radius:4px;font-family:monospace;color:#ffd93d">Alt+R</kbd> Risk Report</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption(
	f"Module: **Nova Sonic** · Mode: **{sonic_status.get('mode', 'unknown')}** · Voice Session Persisted: **Yes** · Commands: **{len(st.session_state.get('nova_voice_history', []))}**"
)

core.finalize_page()
