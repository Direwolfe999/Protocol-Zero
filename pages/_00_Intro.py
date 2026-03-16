"""Intro screen page - shown first."""
from __future__ import annotations

import streamlit as st
import app_core as core

st.set_page_config(page_title="Protocol Zero · Intro", layout="wide", initial_sidebar_state="collapsed")

# If already completed, redirect to dashboard
if st.session_state.get("_intro_completed", False):
    st.switch_page("pages/00_Dashboard.py")

# Initialize
if "_intro_step" not in st.session_state:
    st.session_state["_intro_step"] = 0

# Show intro HTML
core.render_intro_screen()

# Add a hidden button that can be triggered by JavaScript
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("✅ Go to Dashboard", use_container_width=True, key="go_dashboard"):
        st.session_state["_intro_completed"] = True
        st.switch_page("pages/00_Dashboard.py")

