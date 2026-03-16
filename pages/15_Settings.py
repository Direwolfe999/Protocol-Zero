"""
Protocol Zero — Settings & Configuration
==========================================
User-friendly settings page for risk presets, model selection, and exports.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
from datetime import datetime

import app_core as core


st.set_page_config(page_title="⚙️ Settings", page_icon="⚙️", layout="wide")

core.render_shell(current_panel="⚙️  Settings", show_top_row=False)

# ─────────────────────────────────────────────────────────────
# SETTINGS INITIALIZATION
# ─────────────────────────────────────────────────────────────

def _init_settings():
    """Initialize settings in session state."""
    if "settings_initialized" not in st.session_state:
        st.session_state["settings_initialized"] = True
        st.session_state["risk_preset"] = "balanced"
        st.session_state["max_position_usd"] = 500.0
        st.session_state["max_daily_loss_usd"] = 1000.0
        st.session_state["min_confidence_threshold"] = 0.60
        st.session_state["nova_enabled"] = True
        st.session_state["voice_enabled"] = True
        st.session_state["auto_trade_enabled"] = False


_init_settings()


# ─────────────────────────────────────────────────────────────
# SETTINGS SECTIONS
# ─────────────────────────────────────────────────────────────

st.markdown("# ⚙️ Protocol Zero Settings")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Risk Presets",
    "📊 Advanced Risk",
    "🧠 AI & Models",
    "🔊 Voice & Alerts",
    "💾 Backup & Export"
])


# ═══════════════════════════════════════════════════════════
# TAB 1: RISK PRESETS
# ═══════════════════════════════════════════════════════════

with tab1:
    st.markdown("## Risk Management Presets")
    st.markdown("Choose a pre-configured risk profile or customize manually.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        preset = st.radio(
            "Risk Preset",
            ["conservative", "balanced", "aggressive"],
            index=["conservative", "balanced", "aggressive"].index(st.session_state.get("risk_preset", "balanced")),
            help="Pre-configured risk settings"
        )
        st.session_state["risk_preset"] = preset
    
    presets_config = {
        "conservative": {
            "max_position_usd": 250,
            "max_daily_loss_usd": 500,
            "min_confidence": 0.75,
            "description": "🛡️ Capital preservation focus. Only trades with high confidence. Smaller positions.",
        },
        "balanced": {
            "max_position_usd": 500,
            "max_daily_loss_usd": 1000,
            "min_confidence": 0.60,
            "description": "⚖️ Growth & stability balance. Moderate positions. Reasonable confidence threshold.",
        },
        "aggressive": {
            "max_position_usd": 1000,
            "max_daily_loss_usd": 2000,
            "min_confidence": 0.45,
            "description": "🚀 Growth focus. Larger positions. More trades, higher volatility.",
        },
    }
    
    with col2:
        preset_config = presets_config.get(preset, {})
        st.info(preset_config.get("description", ""))
        st.markdown("""
        | Parameter | Value |
        |-----------|-------|
        | Max Position | ${:,.0f} |
        | Daily Loss Limit | ${:,.0f} |
        | Min Confidence | {:.0%} |
        """.format(
            preset_config.get("max_position_usd", 500),
            preset_config.get("max_daily_loss_usd", 1000),
            preset_config.get("min_confidence", 0.60)
        ))
    
    if st.button("✅ Apply Preset", type="primary", use_container_width=True):
        config = presets_config.get(preset, {})
        st.session_state["max_position_usd"] = config.get("max_position_usd", 500)
        st.session_state["max_daily_loss_usd"] = config.get("max_daily_loss_usd", 1000)
        st.session_state["min_confidence_threshold"] = config.get("min_confidence", 0.60)
        st.success(f"✅ Applied {preset.upper()} preset")
        st.rerun()


# ═══════════════════════════════════════════════════════════
# TAB 2: ADVANCED RISK
# ═══════════════════════════════════════════════════════════

with tab2:
    st.markdown("## Advanced Risk Parameters")
    st.markdown("Fine-tune individual risk settings.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Position Sizing")
        max_pos = st.slider(
            "Max Position Size (USD)",
            min_value=100.0,
            max_value=5000.0,
            value=st.session_state["max_position_usd"],
            step=50.0,
            help="Largest single trade allowed"
        )
        st.session_state["max_position_usd"] = max_pos
        
        max_loss = st.slider(
            "Max Daily Loss (USD)",
            min_value=200.0,
            max_value=10000.0,
            value=st.session_state["max_daily_loss_usd"],
            step=100.0,
            help="Stop trading if daily loss exceeds this"
        )
        st.session_state["max_daily_loss_usd"] = max_loss
    
    with col2:
        st.subheader("Trade Filters")
        conf = st.slider(
            "Minimum Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state["min_confidence_threshold"],
            step=0.05,
            format="%.0%",
            help="Only execute if Nova is this confident"
        )
        st.session_state["min_confidence_threshold"] = conf
        
        st.markdown("**Risk Score Limits**")
        st.info("Trades with risk_score > 7/10 are rejected (hard limit)")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Max Position", f"${max_pos:,.0f}", help="Largest single trade")
    with col2:
        st.metric("Daily Loss Limit", f"${max_loss:,.0f}", help="Session stop-loss")
    with col3:
        st.metric("Confidence Floor", f"{conf:.0%}", help="Minimum trade conviction")


# ═══════════════════════════════════════════════════════════
# TAB 3: AI & MODELS
# ═══════════════════════════════════════════════════════════

with tab3:
    st.markdown("## AI Model Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🧠 Reasoning Engine")
        nova_enabled = st.toggle(
            "Enable Nova AI Brain",
            value=st.session_state.get("nova_enabled", True),
            help="Use Amazon Nova Lite for intelligent reasoning"
        )
        st.session_state["nova_enabled"] = nova_enabled
        
        if nova_enabled:
            st.success("✅ Nova Lite (Converse API) enabled")
            st.markdown("""
            Nova Lite will be used for:
            - Market analysis with agentic tool-use
            - Rug-pull scanning
            - Smart contract auditing
            - Scam pattern detection via embeddings
            """)
        else:
            st.warning("⚠️ Fallback to rule-based engine (RSI/SMA)")
    
    with col2:
        st.subheader("🎙️ Voice Intelligence")
        voice_enabled = st.toggle(
            "Enable Voice Commands",
            value=st.session_state.get("voice_enabled", True),
            help="Enable Nova Voice + Web Speech API"
        )
        st.session_state["voice_enabled"] = voice_enabled
        
        if voice_enabled:
            st.success("✅ Voice AI enabled (Nova Sonic)")
            st.markdown("""
            Voice features:
            - Natural language commands
            - Status reports & risk briefs
            - Emergency kill-switch activation
            - Streaming responses
            """)
        else:
            st.info("Voice commands disabled")
    
    st.markdown("---")
    
    st.markdown("### AWS Bedrock Configuration")
    
    aws_col1, aws_col2 = st.columns(2)
    
    with aws_col1:
        aws_configured = st.checkbox(
            "AWS Bedrock Credentials Configured",
            value=False,
            help="Check if you have set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env"
        )
        
        if aws_configured:
            st.success("✅ AWS credentials detected")
            st.markdown("""
            **Services Available:**
            - ✅ Nova Lite (Brain reasoning)
            - ✅ Nova Voice (Text intelligence)
            - ⚠️ Nova Act (Invite-only SDK)
            - ✅ Nova Embeddings (Multimodal analysis)
            """)
        else:
            st.warning("⚠️ AWS credentials not configured")
            st.markdown("""
            To enable full Nova AI:
            1. Get AWS credentials (Bedrock access)
            2. Edit `.env` with your keys
            3. Restart Streamlit
            """)
    
    with aws_col2:
        st.markdown("**Fallback Behavior:**")
        st.markdown("""
        When AWS is unavailable:
        - Brain: Uses rule-based RSI/SMA engine
        - Voice: Text-only responses (no speech)
        - Embeddings: Heuristic scam detection
        - Fully functional, just less AI-powered
        """)


# ═══════════════════════════════════════════════════════════
# TAB 4: VOICE & ALERTS
# ═══════════════════════════════════════════════════════════

with tab4:
    st.markdown("## Voice & Alert Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎙️ Voice Preferences")
        
        voice_speed = st.slider(
            "Voice Speed",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="1.0 = normal, 0.5 = slow, 2.0 = fast"
        )
        
        voice_volume = st.slider(
            "Voice Volume",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.1,
            format="%.0%"
        )
        
        auto_speak_alerts = st.toggle(
            "Auto-speak Alerts",
            value=True,
            help="Automatically speak important alerts"
        )
    
    with col2:
        st.subheader("🔔 Alert Thresholds")
        
        alert_pnl = st.number_input(
            "Alert on Drawdown (%)",
            min_value=1.0,
            max_value=50.0,
            value=10.0,
            step=0.5,
            help="Alert if daily drawdown exceeds this"
        )
        
        alert_vol = st.number_input(
            "Alert on High Volatility (%)",
            min_value=5.0,
            max_value=100.0,
            value=25.0,
            step=1.0,
            help="Alert if 4h volatility spike detected"
        )
        
        st.markdown("**Alert Types**")
        alert_risk = st.toggle("Risk Alerts", value=True)
        alert_execution = st.toggle("Execution Alerts", value=True)
        alert_emergency = st.toggle("Emergency Alerts", value=True, help="Always on for safety")


# ═══════════════════════════════════════════════════════════
# TAB 5: BACKUP & EXPORT
# ═══════════════════════════════════════════════════════════

with tab5:
    st.markdown("## Backup & Export")
    
    st.subheader("📥 Export Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Export as JSON", use_container_width=True):
            settings_dict = {
                "risk_preset": st.session_state.get("risk_preset", "balanced"),
                "max_position_usd": st.session_state.get("max_position_usd", 500),
                "max_daily_loss_usd": st.session_state.get("max_daily_loss_usd", 1000),
                "min_confidence_threshold": st.session_state.get("min_confidence_threshold", 0.60),
                "nova_enabled": st.session_state.get("nova_enabled", True),
                "voice_enabled": st.session_state.get("voice_enabled", True),
                "exported_at": datetime.now().isoformat(),
            }
            
            json_str = json.dumps(settings_dict, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"protocol_zero_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("📄 Export as ENV", use_container_width=True):
            env_lines = [
                f"# Exported {datetime.now()}",
                f"PZ_RISK_PRESET={st.session_state.get('risk_preset', 'balanced')}",
                f"PZ_MAX_POSITION_USD={st.session_state.get('max_position_usd', 500)}",
                f"PZ_MAX_DAILY_LOSS_USD={st.session_state.get('max_daily_loss_usd', 1000)}",
                f"PZ_MIN_CONFIDENCE={st.session_state.get('min_confidence_threshold', 0.60)}",
            ]
            env_str = "\n".join(env_lines)
            st.download_button(
                label="📥 Download .env",
                data=env_str,
                file_name=f"protocol_zero_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.env",
                mime="text/plain"
            )
    
    with col3:
        if st.button("🔄 Reset to Default", use_container_width=True):
            st.session_state["risk_preset"] = "balanced"
            st.session_state["max_position_usd"] = 500.0
            st.session_state["max_daily_loss_usd"] = 1000.0
            st.session_state["min_confidence_threshold"] = 0.60
            st.success("✅ Settings reset to defaults")
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("📤 Import Settings")
    
    uploaded_file = st.file_uploader(
        "Upload a JSON settings file",
        type=["json"],
        help="Load previously exported settings"
    )
    
    if uploaded_file:
        try:
            settings = json.load(uploaded_file)
            st.session_state["risk_preset"] = settings.get("risk_preset", "balanced")
            st.session_state["max_position_usd"] = settings.get("max_position_usd", 500)
            st.session_state["max_daily_loss_usd"] = settings.get("max_daily_loss_usd", 1000)
            st.session_state["min_confidence_threshold"] = settings.get("min_confidence_threshold", 0.60)
            st.success("✅ Settings imported successfully")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Import failed: {e}")
    
    st.markdown("---")
    
    st.subheader("📊 Current Settings Summary")
    
    summary = {
        "Risk Preset": st.session_state.get("risk_preset", "balanced"),
        "Max Position": f"${st.session_state.get('max_position_usd', 500):,.0f}",
        "Daily Loss Limit": f"${st.session_state.get('max_daily_loss_usd', 1000):,.0f}",
        "Confidence Threshold": f"{st.session_state.get('min_confidence_threshold', 0.60):.0%}",
        "Nova AI": "🟢 Enabled" if st.session_state.get("nova_enabled", True) else "🔴 Disabled",
        "Voice Commands": "🟢 Enabled" if st.session_state.get("voice_enabled", True) else "🔴 Disabled",
    }
    
    for key, value in summary.items():
        st.markdown(f"**{key}:** {value}")


# ─────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
💡 **Tip:** Settings are stored in your session. To make them permanent, export to JSON 
and add to your `.env` file, then restart Streamlit.
""")
