from __future__ import annotations

import streamlit as st

import app_core as core
from risk_execution_panel import render_risk_execution_panel


df = core.render_shell(current_panel="🛡️  Risk & Exec", show_top_row=True)
flags = core.module_flags()

render_risk_execution_panel(
	df=df,
	run_analysis=core.run_analysis,
	mcard=core.mcard,
	risk_heatmap_html=core.risk_heatmap_html,
	risk_router_html=core.risk_router_html,
	simulate_trade=core.simulate_trade,
	cog=core.cog,
	real_execute_trade=core.real_execute_trade,
	has_chain=bool(flags["has_chain"]),
	chain_obj=flags["chain"],
	logger=core.logger,
)

core.finalize_page()
