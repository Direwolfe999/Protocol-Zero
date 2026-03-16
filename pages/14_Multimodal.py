from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

import app_core as core


core.render_shell(current_panel="🖼️  Multimodal", show_top_row=True)
flags = core.module_flags()
embed = flags.get("nova_embed")

st.markdown("### 🖼️ Nova Embeddings — Multimodal Scam Detection")
st.caption("Analyze text, images, logos & charts for scam patterns using Amazon Nova Multimodal Embeddings")

if not flags.get("has_nova_embed") or embed is None:
	st.warning("⚠️ Nova Embeddings module not loaded. Ensure AWS credentials are configured.")
else:
	embed_mode = st.radio(
		"Analysis Mode",
		["📝 Text Analysis", "🖼️ Image Analysis", "🔍 Logo Comparison", "📊 Chart Analysis"],
		horizontal=True,
		key="embed_mode",
	)

	if embed_mode == "📝 Text Analysis":
		embed_text = st.text_area(
			"Paste token description, whitepaper excerpt, or social media post",
			height=120,
			placeholder="Example: SafeMoon 2.0 — 1000x guaranteed returns! Locked liquidity for 1 week. Dev team anonymous.",
			key="embed_text_input",
		)
		if st.button("🔍 Analyze Text", key="btn_embed_text", type="primary") and embed_text:
			try:
				result = embed.analyze_text(embed_text)
				st.session_state["nova_embed_results"].append(
					{
						"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
						"mode": "text",
						"input_preview": embed_text[:80],
						"result": result.__dict__ if hasattr(result, "__dict__") else result,
					}
				)
				core.cog("✓", f"Text analysis — risk: {getattr(result, 'risk_label', 'N/A')}", "ok")
			except Exception as e:
				st.error(f"Analysis failed: {e}")

	elif embed_mode == "🖼️ Image Analysis":
		img_url = st.text_input("Image URL or Base64", placeholder="https://example.com/token-logo.png", key="embed_img_input")
		if st.button("🔍 Analyze Image", key="btn_embed_img", type="primary") and img_url:
			try:
				result = embed.analyze_image(img_url.encode("utf-8"), context=img_url)
				st.session_state["nova_embed_results"].append(
					{
						"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
						"mode": "image",
						"input_preview": img_url[:80],
						"result": result.__dict__ if hasattr(result, "__dict__") else result,
					}
				)
				core.cog("✓", f"Image analysis — risk: {getattr(result, 'risk_label', 'N/A')}", "ok")
			except Exception as e:
				st.error(f"Analysis failed: {e}")

	elif embed_mode == "🔍 Logo Comparison":
		lc1, lc2 = st.columns(2)
		with lc1:
			logo_url1 = st.text_input("Reference Logo URL", placeholder="Official project logo URL", key="logo1")
		with lc2:
			logo_url2 = st.text_input("Suspect Logo URL", placeholder="Suspicious token logo URL", key="logo2")
		if st.button("🔍 Compare Logos", key="btn_compare_logos", type="primary") and logo_url1 and logo_url2:
			try:
				result = embed.compare_logos(logo_url1.encode("utf-8"), reference_name=logo_url2)
				st.session_state["nova_embed_results"].append(
					{
						"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
						"mode": "logo_compare",
						"input_preview": f"{logo_url1[:30]}… vs {logo_url2[:30]}…",
						"result": result.__dict__ if hasattr(result, "__dict__") else result,
					}
				)
				core.cog("✓", "Logo comparison complete", "ok")
			except Exception as e:
				st.error(f"Comparison failed: {e}")

	else:
		chart_url = st.text_input("Chart Image URL", placeholder="URL to trading chart screenshot", key="chart_url_input")
		if st.button("🔍 Analyze Chart", key="btn_chart_analyze", type="primary") and chart_url:
			try:
				result = embed.analyze_chart(chart_url.encode("utf-8"))
				st.session_state["nova_embed_results"].append(
					{
						"timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
						"mode": "chart",
						"input_preview": chart_url[:80],
						"result": result.__dict__ if hasattr(result, "__dict__") else result,
					}
				)
				core.cog("✓", f"Chart analysis — risk: {getattr(result, 'risk_label', 'N/A')}", "ok")
			except Exception as e:
				st.error(f"Analysis failed: {e}")

	st.markdown('<div class="hz"></div>', unsafe_allow_html=True)
	st.markdown("#### 📊 Analysis Results")
	results = st.session_state.get("nova_embed_results", [])
	if results:
		latest = results[-1]
		er = latest["result"]
		risk_label = er.get("risk_label", "UNKNOWN")
		sim_score = er.get("similarity_score", 0)
		colors = {"SAFE": "#64ffda", "LOW_RISK": "#64ffda", "MEDIUM_RISK": "#ffd93d", "HIGH_RISK": "#ff6b6b", "CRITICAL": "#ff0040", "UNKNOWN": "#8892b0"}
		erc = colors.get(risk_label, "#8892b0")

		st.markdown(
			f"""
			<div style="background:linear-gradient(135deg, rgba(6,6,18,0.95), rgba(26,26,62,0.8));
						border:1px solid {erc}40;border-radius:12px;padding:1.5rem;margin:1rem 0;
						text-align:center">
				<div style="font-size:2rem;margin-bottom:0.3rem">🖼️</div>
				<div style="font-size:1.5rem;font-weight:700;color:{erc}">{risk_label}</div>
				<div style="font-size:0.85rem;color:#8892b0;margin-top:0.3rem">
					Similarity Score: <b>{sim_score:.2f}</b> · Mode: <b>{latest['mode']}</b> ·
					<span style="color:#495670">{latest['timestamp']}</span></div>
			</div>
			""",
			unsafe_allow_html=True,
		)

		findings = er.get("findings", []) if isinstance(er, dict) else []
		if findings:
			st.markdown("##### 🔎 Findings")
			for f_item in findings:
				if isinstance(f_item, dict):
					f_name = f_item.get("pattern_name", f_item.get("name", "Unknown"))
					f_sim = f_item.get("similarity", 0)
					f_cat = f_item.get("category", "")
					f_sev = f_item.get("severity", "medium")
					sev_colors = {"low": "#64ffda", "medium": "#ffd93d", "high": "#ff6b6b", "critical": "#ff0040"}
					sc = sev_colors.get(f_sev, "#8892b0")
					st.markdown(
						f'<div style="border-left:3px solid {sc};padding:0.5rem 0.8rem;margin:0.3rem 0;background:rgba(6,6,18,0.5);border-radius:0 6px 6px 0"><div style="display:flex;justify-content:space-between"><span style="color:#ccd6f6;font-weight:600;font-size:0.85rem">{f_name}</span><span style="color:{sc};font-size:0.75rem;font-weight:600">{str(f_sev).upper()}</span></div><div style="color:#8892b0;font-size:0.72rem;margin-top:0.2rem">Category: {f_cat} · Similarity: {f_sim:.2f}</div></div>',
						unsafe_allow_html=True,
					)

		if len(results) > 1:
			st.markdown("##### 📋 Analysis History")
			for he in reversed(results[:-1]):
				hr = he["result"]
				hrl = hr.get("risk_label", "?")
				hrc = colors.get(hrl, "#495670")
				st.markdown(
					f'<div style="border-left:3px solid {hrc};padding:0.3rem 0.8rem;margin:0.2rem 0;font-size:0.72rem;color:#8892b0"><b style="color:{hrc}">{hrl}</b> · {he["mode"]} · {he["input_preview"][:40]}… · <span style="color:#495670">{he["timestamp"]}</span></div>',
					unsafe_allow_html=True,
				)
	else:
		st.info("Select an analysis mode and submit content to analyze.")

core.finalize_page()
