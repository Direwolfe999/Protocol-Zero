from __future__ import annotations

import numpy as np
import streamlit as st

import app_core as core


core.render_shell(current_panel="🔍  History", show_top_row=True)

st.markdown("### 🔍 AI Decision History")
st.caption("Full feed of AI decisions with profitability annotations")

# Use the new decision_feed_html() function for consistent rendering
st.markdown(core.decision_feed_html(limit=50), unsafe_allow_html=True)

core.finalize_page()
