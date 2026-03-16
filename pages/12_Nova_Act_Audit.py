from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

import streamlit as st

import app_core as core


core.render_shell(current_panel="🔍  Nova Act Audit", show_top_row=True)
flags = core.module_flags()
nova_act = flags.get("nova_act")

st.markdown("### 🔍 Nova Act — Smart Contract Auditor")
st.caption("Browser-based automated contract & token auditing via Amazon Nova Act")

if not flags.get("has_nova_act") or nova_act is None:
	st.warning("⚠️ Nova Act module not loaded. Install `nova-act` and configure credentials.")
else:
	na_col1, na_col2 = st.columns([2, 1])
	with na_col1:
		audit_address = st.text_input(
			"Contract / Token Address",
			placeholder="0x...",
			key="nova_act_address",
		)
	with na_col2:
		st.markdown("<br>", unsafe_allow_html=True)
		audit_type = st.radio(
			"Audit Type",
			["Contract", "Token", "Quick Safety"],
			horizontal=True,
			key="nova_act_type",
		)

	if st.button("🔍 Run Nova Act Audit", key="btn_nova_audit", type="primary"):
		if not audit_address or len(audit_address) < 10:
			st.error("Please enter a valid contract address.")
		else:
			with st.spinner("🤖 Nova Act is automating browser-based audit…"):
				core.cog("🔍", f"Nova Act auditing {audit_address[:16]}…", "info")
				try:
					if audit_type == "Contract":
						result = nova_act.audit_contract(audit_address)
					elif audit_type == "Token":
						result = nova_act.audit_token(audit_address)
					else:
						result = nova_act.quick_safety_check(audit_address)

					entry = {
						"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
						"address": audit_address,
						"type": audit_type,
						"result": result.__dict__ if hasattr(result, "__dict__") else result,
					}
					st.session_state["nova_act_results"].append(entry)
					core.cog("✓", f"Audit complete — risk: {getattr(result, 'risk_level', 'N/A')}", "ok")
				except Exception as e:
					st.error(f"Audit failed: {e}")
					core.cog("✗", f"Nova Act error: {e}", "err")

	results = st.session_state.get("nova_act_results", [])
	if results:
		latest = results[-1]
		r = latest["result"]
		risk_lev = r.get("risk_level", "UNKNOWN")
		risk_sc = r.get("risk_score", 0)
		risk_colors = {"LOW": "#64ffda", "MEDIUM": "#ffd93d", "HIGH": "#ff6b6b", "CRITICAL": "#ff0040"}
		rc = risk_colors.get(risk_lev, "#8892b0")
		st.markdown(
			f"""
			<div style="background:linear-gradient(135deg, rgba(6,6,18,0.95), rgba(26,26,62,0.8));
						border:1px solid {rc}40;border-radius:12px;padding:1.5rem;margin:1rem 0;
						text-align:center">
				<div style="font-size:2.5rem;margin-bottom:0.3rem">🛡️</div>
				<div style="font-size:1.8rem;font-weight:700;color:{rc}">{risk_lev}</div>
				<div style="font-size:0.9rem;color:#8892b0;margin-top:0.3rem">
					Risk Score: <b>{risk_sc}/100</b> · {latest['type']} Audit ·
					<span style="color:#495670">{latest['address'][:20]}…</span></div>
			</div>
			""",
			unsafe_allow_html=True,
		)

		ac1, ac2, ac3, ac4 = st.columns(4)
		warnings = r.get("warning_banners", []) if isinstance(r, dict) else []
		with ac1:
			cv = bool(r.get("contract_verified", False))
			st.markdown(core.mcard("Contract Verified", "✅ Yes" if cv else "❌ No", "", cv), unsafe_allow_html=True)
		with ac2:
			ll = bool(r.get("liquidity_locked", False))
			st.markdown(core.mcard("Liquidity Locked", "✅ Yes" if ll else "❌ No", "", ll), unsafe_allow_html=True)
		with ac3:
			st.markdown(core.mcard("Warnings", str(len(warnings)), "Detected", len(warnings) == 0), unsafe_allow_html=True)
		with ac4:
			sf = r.get("social_flags", []) if isinstance(r, dict) else []
			st.markdown(core.mcard("Social Flags", str(len(sf)), "Issues", len(sf) == 0), unsafe_allow_html=True)

		if warnings:
			st.markdown("#### ⚠️ Warning Banners Detected")
			for w in warnings:
				st.markdown(
					f'<div style="background:#ff6b6b10;border-left:3px solid #ff6b6b;padding:0.5rem 0.8rem;margin:0.3rem 0;border-radius:0 6px 6px 0;color:#ff9999;font-size:0.8rem">⚠️ {w}</div>',
					unsafe_allow_html=True,
				)

		if len(results) > 1:
			st.markdown("#### 📋 Audit History")
			for h_entry in reversed(results[:-1]):
				hr = h_entry["result"]
				hrc = risk_colors.get(hr.get("risk_level", ""), "#495670")
				st.markdown(
					f'<div style="border-left:3px solid {hrc};padding:0.4rem 0.8rem;margin:0.2rem 0;font-size:0.75rem;color:#8892b0"><b style="color:{hrc}">{hr.get("risk_level", "?")}</b> · {h_entry["type"]} · {h_entry["address"][:18]}… · <span style="color:#495670">{h_entry["timestamp"]}</span></div>',
					unsafe_allow_html=True,
				)
	else:
		st.info("Enter a contract address and run a Nova Act audit.")

if flags.get("has_nova_act") and nova_act is not None:
	st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
	act_status = nova_act.status()
	st.caption(
		f"Module: **Nova Act** · Mode: **{act_status.get('mode', 'unknown')}** · Total Audits: **{len(st.session_state.get('nova_act_results', []))}**"
	)

core.finalize_page()
