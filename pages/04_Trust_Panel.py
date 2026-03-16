from __future__ import annotations

import time

import streamlit as st

import app_core as core


core.render_shell(current_panel="🌐  Trust Panel", show_top_row=True)
flags = core.module_flags()

st.markdown("### 🌐 ERC-8004 On-Chain Trust Panel")
st.caption("Live trust data from Identity, Reputation, and Validation registries")

if "_trust_cache" not in st.session_state:
	st.session_state["_trust_cache"] = {
		"identity": core.fetch_on_chain_identity(),
		"reputation": core.fetch_on_chain_reputation(),
		"validation": core.fetch_validation_summary(),
	}
	st.session_state["_trust_cache_ts"] = time.time()

if st.button("🔄 Refresh Trust Data", key="refresh_trust"):
	st.session_state["_trust_cache"] = {
		"identity": core.fetch_on_chain_identity(),
		"reputation": core.fetch_on_chain_reputation(),
		"validation": core.fetch_validation_summary(),
	}
	st.session_state["_trust_cache_ts"] = time.time()

identity_data = st.session_state["_trust_cache"]["identity"]
rep_data = st.session_state["_trust_cache"]["reputation"]
val_data = st.session_state["_trust_cache"]["validation"]

st.markdown("#### 🆔 Identity Registry")
ic1, ic2, ic3 = st.columns(3)
with ic1:
	reg_status = "✅ REGISTERED" if identity_data.get("registered") else "❌ NOT REGISTERED"
	reg_color = "#64ffda" if identity_data.get("registered") else "#ff6b6b"
	st.markdown(f'<div class="mcard"><div class="lbl">Identity Status</div><div class="val" style="color:{reg_color};font-size:1rem">{reg_status}</div></div>', unsafe_allow_html=True)
with ic2:
	st.markdown(core.mcard("Token ID", str(identity_data.get("token_id") or "—")), unsafe_allow_html=True)
with ic3:
	st.markdown(core.mcard("Network", "Sepolia (11155111)" if flags["has_chain"] else "Not Connected"), unsafe_allow_html=True)

st.markdown("#### ⭐ Reputation + Validation")
rc1, rc2, rc3, rc4 = st.columns(4)
score = rep_data.get("score") if rep_data.get("score") is not None else st.session_state.get("reputation_score", 95)
with rc1:
	st.markdown(core.mcard("Trust Score", str(score)), unsafe_allow_html=True)
with rc2:
	st.markdown(core.mcard("Feedback Count", str(rep_data.get("count", 0))), unsafe_allow_html=True)
with rc3:
	st.markdown(core.mcard("Validations", str(val_data.get("total", 0))), unsafe_allow_html=True)
with rc4:
	total = int(val_data.get("total", 0) or 0)
	approved = int(val_data.get("approved", 0) or 0)
	ar = (approved / total * 100) if total > 0 else 0
	st.markdown(core.mcard("Approval Rate", f"{ar:.0f}%"), unsafe_allow_html=True)

st.markdown("#### 🔌 Module Status")
mods = [
	("Chain", flags["has_chain"]),
	("Performance", flags["has_perf"]),
	("Artifacts", flags["has_artifacts"]),
	("Risk", flags["has_risk"]),
	("Sign", flags["has_sign"]),
	("DEX", flags["has_dex"]),
	("Nova Act", flags["has_nova_act"]),
	("Nova Sonic", flags["has_nova_sonic"]),
	("Nova Embed", flags["has_nova_embed"]),
]

cols = st.columns(3)
for i, (name, ok) in enumerate(mods):
	with cols[i % 3]:
		color = "#64ffda" if ok else "#ff6b6b"
		status = "LIVE" if ok else "OFF"
		st.markdown(f'<div class="mcard" style="border-left:3px solid {color}"><div class="lbl">{name}</div><div class="val" style="font-size:.95rem;color:{color}">{status}</div></div>', unsafe_allow_html=True)

core.finalize_page()
