"""Streamlit Cloud entrypoint for Protocol Zero.

This entrypoint bootstraps safe defaults so Streamlit Community Cloud can
always start the dashboard, even when full blockchain/AWS secrets are absent.
Real secrets (if configured) still take precedence.
"""

from __future__ import annotations

import os
import streamlit as st


def _set_default_env(key: str, value: str) -> None:
	"""Set env var only when not already provided by the host/secrets."""
	if not os.getenv(key):
		os.environ[key] = value


# ── Cloud-safe defaults (non-destructive; real secrets override these) ──
_set_default_env("PZ_CLOUD_SAFE_MODE", "1")
_set_default_env("PZ_FORCE_DASHBOARD_MODE", "1")

# Required config vars (for graceful dashboard boot on Streamlit Cloud)
_set_default_env("RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
_set_default_env(
	"PRIVATE_KEY",
	"1111111111111111111111111111111111111111111111111111111111111111",
)
_set_default_env("IDENTITY_REGISTRY_ADDRESS", "0x000000000000000000000000000000000000dEaD")
_set_default_env("REPUTATION_REGISTRY_ADDRESS", "0x000000000000000000000000000000000000bEEF")
_set_default_env("VALIDATION_REGISTRY_ADDRESS", "0x000000000000000000000000000000000000c0Fe")
_set_default_env("CHAIN_ID", "11155111")
_set_default_env("DEX_ENABLED", "false")

# Dashboard module should not call page config when loaded via multipage router.
os.environ["PZ_SKIP_PAGE_CONFIG"] = "1"

st.set_page_config(
	page_title="Protocol Zero · Autonomous Agent",
	page_icon="🛡️",
	layout="wide",
	initial_sidebar_state="collapsed",
)

# === GLOBAL STYLE ===
st.markdown("""
<style>
.st-emotion-cache-1p-yk96 { max-width: 100%; padding: 1rem; }
[data-testid="stSidebarNav"] { display: none !important; }
.stApp > header { background-color: transparent !important; }
div[data-testid="stVerticalBlock"] > div:nth-of-type(n+1) { margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if not st.session_state.get("_app_initialized", False):
	st.session_state["_app_initialized"] = True
	st.session_state["_intro_completed"] = False

# If intro not completed, show it and stop
if not st.session_state.get("_intro_completed", False):
	st.switch_page("pages/_00_Intro.py")

pages = [
	st.Page("pages/00_Dashboard.py", title="🛡️ Dashboard", icon="🛡️"),
	st.Page("pages/01_Market.py", title="📊 Market", icon="📊"),
	st.Page("pages/02_AI_Brain.py", title="🧠 AI Brain", icon="🧠"),
	st.Page("pages/03_Risk_Execution.py", title="⚡ Risk & Exec", icon="⚡"),
	st.Page("pages/04_Trust_Panel.py", title="🌐 Trust Panel", icon="🌐"),
	st.Page("pages/05_Performance.py", title="📈 Performance", icon="📈"),
	st.Page("pages/06_Audit_Trail.py", title="🔗 Audit Trail", icon="🔗"),
	st.Page("pages/07_Calibration.py", title="🎯 Calibration", icon="🎯"),
	st.Page("pages/08_Microstructure.py", title="📡 Microstructure", icon="📡"),
	st.Page("pages/09_TX_Log.py", title="📒 TX Log", icon="📒"),
	st.Page("pages/10_PnL.py", title="💹 P&L", icon="💹"),
	st.Page("pages/11_History.py", title="🕘 History", icon="🕘"),
	st.Page("pages/12_Nova_Act_Audit.py", title="🔍 Nova Audit", icon="🔍"),
	st.Page("pages/13_Voice_AI.py", title="🎙️ Voice AI", icon="🎙️"),
	st.Page("pages/14_Multimodal.py", title="🖼️ Multimodal", icon="🖼️"),
]

pg = st.navigation(pages)
pg.run()
