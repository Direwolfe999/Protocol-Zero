from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timezone

import streamlit as st

import app_core as core


core.render_shell(current_panel="🔗  Audit Trail", show_top_row=True)

st.markdown("### 🔗 Cryptographic Audit Trail")
st.caption("Each decision sealed with keccak256 hashes and optional EIP-712 signatures")

artifacts = core.load_artifacts()
if artifacts:
	n_signed = sum(1 for a in artifacts if (a.get("signedIntent", {}).get("signature") or "").strip())
	n_unsigned = len(artifacts) - n_signed
	latest_hash = (artifacts[0].get("artifactHash", "") or "")[:24] or "—"

	ac1, ac2, ac3, ac4 = st.columns(4)
	with ac1:
		st.markdown(core.mcard("Total Artifacts", str(len(artifacts))), unsafe_allow_html=True)
	with ac2:
		st.markdown(core.mcard("🔏 Signed", str(n_signed)), unsafe_allow_html=True)
	with ac3:
		st.markdown(core.mcard("📋 Unsigned", str(n_unsigned)), unsafe_allow_html=True)
	with ac4:
		st.markdown(core.mcard("Latest Hash", f"{latest_hash}…"), unsafe_allow_html=True)

	art_json = json.dumps(artifacts, indent=2, default=str)
	st.download_button(
		"📥 Export Artifacts (JSON)",
		data=art_json,
		file_name=f"protocol_zero_artifacts_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.json",
		mime="application/json",
	)

	for i, art in enumerate(artifacts[:10]):
		art_hash = art.get("artifactHash", art.get("artifact_hash", ""))[:16] or "unknown"
		art_time = art.get("timestamp", art.get("created_at", "?"))
		action = art.get("decision", {}).get("action", "?")
		asset = art.get("decision", {}).get("asset", "?")
		conf = art.get("decision", {}).get("confidence", 0)
		signed = bool((art.get("signedIntent", {}).get("signature") or "").strip())
		css = {"BUY": "dec-buy", "SELL": "dec-sell"}.get(action, "dec-hold")
		badge = '<span class="badge badge-green">🔏 Signed</span>' if signed else '<span class="badge badge-gold">📋 Unsigned</span>'
		st.markdown(
			f"""
			<div class="dec-box {css}" style="padding:.8rem 1rem;margin:.3rem 0">
				<div style="display:flex;justify-content:space-between;align-items:center">
					<span style="font-size:.9rem;font-weight:700">{action} {asset} <span style="font-size:.7rem;color:#495670">Conf: {conf:.0%}</span></span>
					<span style="color:#495670;font-size:.7rem">{art_time}</span>
				</div>
				<div style="margin-top:.4rem;font-size:.72rem">
					<span style="color:#8892b0">Hash:</span>
					<span style="color:#b388ff"> {art_hash}…</span>
					<span style="margin-left:12px">{badge}</span>
				</div>
			</div>
			""",
			unsafe_allow_html=True,
		)
		with st.expander(f"🔍 Artifact #{i + 1} — Full Details"):
			st.json(art)

if not artifacts:
	st.info("Execute trades to generate cryptographic validation artifacts.")

core.finalize_page()
