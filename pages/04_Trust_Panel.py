from __future__ import annotations

import time
from datetime import datetime, timezone

import plotly.graph_objects as go
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
	tier = "🥇 Elite" if int(score) >= 90 else ("🥈 Trusted" if int(score) >= 70 else ("🥉 Standard" if int(score) >= 40 else "⚠️ Unproven"))
	st.markdown(core.mcard("Trust Tier", tier), unsafe_allow_html=True)
with rc4:
	st.markdown(core.mcard("Validations", str(val_data.get("total", 0))), unsafe_allow_html=True)

st.markdown("#### 📈 Trust Score Evolution")
trust_hist = st.session_state.get("trust_history", [])
trust_hist.append(
	{
		"time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
		"score": int(score),
	}
)
st.session_state["trust_history"] = trust_hist[-50:]

if len(trust_hist) > 1:
	fig_trust = go.Figure()
	fig_trust.add_trace(
		go.Scatter(
			x=[t["time"] for t in trust_hist],
			y=[t["score"] for t in trust_hist],
			fill="tozeroy",
			mode="lines+markers",
			line=dict(color="#64ffda", width=2),
			fillcolor="rgba(100,255,218,0.08)",
			marker=dict(size=5, color="#64ffda"),
		)
	)
	fig_trust.add_hline(y=70, line_dash="dash", line_color="#ffd93d", annotation_text="Trusted Threshold")
	fig_trust.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0,0,0,0)",
		plot_bgcolor="rgba(6,6,18,0.9)",
		height=250,
		margin=dict(l=0, r=0, t=10, b=0),
		yaxis=dict(gridcolor="#111130", range=[0, 105], title="Trust Score"),
		xaxis=dict(gridcolor="#111130"),
	)
	st.plotly_chart(fig_trust, use_container_width=True)

st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
st.markdown("#### ✅ Validation Registry")
vc1, vc2, vc3 = st.columns(3)
with vc1:
	st.markdown(core.mcard("Total Requests", str(val_data.get("total", 0))), unsafe_allow_html=True)
with vc2:
	st.markdown(core.mcard("Approved", str(val_data.get("approved", 0))), unsafe_allow_html=True)
with vc3:
	total = int(val_data.get("total", 0) or 0)
	approved = int(val_data.get("approved", 0) or 0)
	ar = (approved / total * 100) if total > 0 else 0
	st.markdown(core.mcard("Approval Rate", f"{ar:.0f}%"), unsafe_allow_html=True)

st.markdown("#### 🔌 Module Status")
mods = [
	("Chain Interactor", flags["has_chain"]),
	("Performance Tracker", flags["has_perf"]),
	("Validation Artifacts", flags["has_artifacts"]),
	("Risk Check", flags["has_risk"]),
	("Sign Trade", flags["has_sign"]),
	("DEX Executor", flags["has_dex"]),
	("Nova Act", flags["has_nova_act"]),
	("Nova Sonic", flags["has_nova_sonic"]),
	("Nova Embed", flags["has_nova_embed"]),
]

mod_cards = ""
for name, connected in mods:
	icon = "🟢" if connected else "🔴"
	cls = "mod-on" if connected else "mod-off"
	tag = "LIVE" if connected else "OFF"
	mod_cards += (
		f'<div class="mod-card {cls}">'
		f'<span class="mod-icon">{icon}</span>'
		f'<span class="mod-name">{name}</span>'
		f'<span class="mod-tag">{tag}</span>'
		f'</div>'
	)

st.markdown(f'<div class="mod-grid">{mod_cards}</div>', unsafe_allow_html=True)

st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
st.markdown("#### 💰 DEX Wallet Balances")

dex_status_icon = "🟢 ENABLED" if st.session_state.get("dex_enabled") else "🔴 DISABLED"
dex_sc = "#64ffda" if st.session_state.get("dex_enabled") else "#ff6b6b"
wc1, wc2, wc3, wc4 = st.columns(4)
with wc1:
	st.markdown(
		f'<div class="mcard"><div class="lbl">DEX Status</div><div class="val" style="color:{dex_sc};font-size:0.9rem">{dex_status_icon}</div></div>',
		unsafe_allow_html=True,
	)
with wc2:
	st.markdown(core.mcard("ETH", f"{float(st.session_state.get('wallet_eth', 0.0)):.4f}"), unsafe_allow_html=True)
with wc3:
	st.markdown(core.mcard("WETH", f"{float(st.session_state.get('wallet_weth', 0.0)):.4f}"), unsafe_allow_html=True)
with wc4:
	st.markdown(core.mcard("USDC", f"{float(st.session_state.get('wallet_usdc', 0.0)):.2f}"), unsafe_allow_html=True)

core.finalize_page()
