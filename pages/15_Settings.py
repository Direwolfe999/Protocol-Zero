"""
⚙️ Settings
Risk management, model configuration, and user preferences
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
from datetime import datetime, timezone

import app_core as core

core.render_shell(current_panel="⚙️  Settings", show_top_row=True)

st.title("⚙️ Settings & Configuration")

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Risk Management", "🤖 AI Model", "📊 Display", "💾 Export"])

# ============================================================================
# TAB 1: RISK MANAGEMENT
# ============================================================================
with tab1:
    st.markdown("### Risk Configuration")
    
    # Risk presets
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🟢 Conservative", use_container_width=True, key="preset_conservative"):
            st.session_state["risk_preset"] = "conservative"
            st.session_state["max_position_size"] = 0.05  # 5%
            st.session_state["daily_loss_limit"] = 500    # $500
            st.session_state["min_confidence"] = 0.75     # 75%
            st.success("✅ Conservative preset applied")
    
    with col2:
        if st.button("🟡 Balanced", use_container_width=True, key="preset_balanced"):
            st.session_state["risk_preset"] = "balanced"
            st.session_state["max_position_size"] = 0.10  # 10%
            st.session_state["daily_loss_limit"] = 1000   # $1000
            st.session_state["min_confidence"] = 0.60     # 60%
            st.success("✅ Balanced preset applied")
    
    with col3:
        if st.button("🔴 Aggressive", use_container_width=True, key="preset_aggressive"):
            st.session_state["risk_preset"] = "aggressive"
            st.session_state["max_position_size"] = 0.20  # 20%
            st.session_state["daily_loss_limit"] = 2000   # $2000
            st.session_state["min_confidence"] = 0.40     # 40%
            st.success("✅ Aggressive preset applied")
    
    st.divider()
    
    # Custom risk sliders
    st.markdown("### Custom Risk Parameters")
    
    current_preset = st.session_state.get("risk_preset", "balanced")
    st.info(f"Current preset: **{current_preset.title()}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_pos = st.slider(
            "Max Position Size (%)",
            min_value=1,
            max_value=50,
            value=st.session_state.get("max_position_size", 0.10) * 100,
            step=1,
            help="Maximum percentage of capital per trade"
        ) / 100
        st.session_state["max_position_size"] = max_pos
        st.metric("Position Limit", f"${max_pos * st.session_state.get('total_capital_usd', 10000):.2f}")
    
    with col2:
        daily_loss = st.slider(
            "Daily Loss Limit ($)",
            min_value=100,
            max_value=5000,
            value=int(st.session_state.get("daily_loss_limit", 1000)),
            step=100,
            help="Max drawdown allowed per day"
        )
        st.session_state["daily_loss_limit"] = daily_loss
        st.metric("Daily Cap", f"${daily_loss:.2f}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_conf = st.slider(
            "Minimum Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.get("min_confidence", 0.60),
            step=0.05,
            format="%.0f%%",
            help="Only execute trades with ≥ this confidence"
        )
        st.session_state["min_confidence"] = min_conf
        st.metric("Confidence Floor", f"{min_conf*100:.0f}%")
    
    with col2:
        max_freq = st.slider(
            "Max Trades Per Day",
            min_value=1,
            max_value=100,
            value=st.session_state.get("max_trades_per_day", 20),
            step=1,
            help="Maximum number of trades in 24h window"
        )
        st.session_state["max_trades_per_day"] = max_freq
        st.metric("Trade Frequency", f"{max_freq} trades/day")
    
    st.divider()
    
    # Risk thresholds
    st.markdown("### Risk Thresholds (Expert Mode)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_concentration = st.slider(
            "Max Concentration (% per asset)",
            min_value=10,
            max_value=100,
            value=st.session_state.get("max_concentration", 50),
            step=5
        )
        st.session_state["max_concentration"] = max_concentration
    
    with col2:
        drawdown_tolerance = st.slider(
            "Drawdown Tolerance (%)",
            min_value=5,
            max_value=50,
            value=st.session_state.get("drawdown_tolerance", 20),
            step=5
        )
        st.session_state["drawdown_tolerance"] = drawdown_tolerance

# ============================================================================
# TAB 2: AI MODEL SETTINGS
# ============================================================================
with tab2:
    st.markdown("### AI Model Configuration")
    
    model_type = st.radio(
        "Nova Model Selection",
        options=["🤖 Nova Lite (Real)", "⚡ Fallback (Heuristic)"],
        help="Nova Lite uses real AWS Bedrock API. Fallback uses rule-based reasoning."
    )
    st.session_state["nova_model"] = "lite" if "Real" in model_type else "fallback"
    
    if st.session_state["nova_model"] == "lite":
        st.success("🟢 Using Nova Lite (Bedrock API)")
        st.info("""
        Requirements:
        - AWS account with Bedrock access
        - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
        - Region: us-east-1 (Nova Lite availability)
        """)
    else:
        st.warning("🟡 Using fallback heuristic reasoning")
        st.info("""
        Fallback mode:
        - No AWS credentials needed
        - Uses rule-based decision logic
        - Great for testing and demos
        - Full compatibility with risk gates
        """)
    
    st.divider()
    
    st.markdown("### Reasoning Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        temperature = st.slider(
            "Model Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.get("nova_temperature", 0.7),
            step=0.1,
            help="Higher = more creative, Lower = more deterministic"
        )
        st.session_state["nova_temperature"] = temperature
    
    with col2:
        max_tokens = st.slider(
            "Max Reasoning Tokens",
            min_value=100,
            max_value=1000,
            value=st.session_state.get("nova_max_tokens", 500),
            step=50
        )
        st.session_state["nova_max_tokens"] = max_tokens
    
    st.markdown("### Voice AI Settings")
    
    voice_enabled = st.checkbox(
        "Enable Voice Commands",
        value=st.session_state.get("voice_enabled", True),
        help="Allow Alt+V voice activation on all pages"
    )
    st.session_state["voice_enabled"] = voice_enabled
    
    voice_notifications = st.checkbox(
        "Voice Notifications",
        value=st.session_state.get("voice_notifications", True),
        help="Audio feedback for trades and alerts"
    )
    st.session_state["voice_notifications"] = voice_notifications

# ============================================================================
# TAB 3: DISPLAY SETTINGS
# ============================================================================
with tab3:
    st.markdown("### Display Preferences")
    
    theme = st.radio(
        "Theme",
        options=["🌙 Dark (Default)", "☀️ Light"],
        help="Choose color scheme for the dashboard"
    )
    st.session_state["theme"] = "dark" if "Dark" in theme else "light"
    
    st.divider()
    
    st.markdown("### Accessibility")
    
    col1, col2 = st.columns(2)
    
    with col1:
        high_contrast = st.checkbox(
            "High Contrast Mode",
            value=st.session_state.get("high_contrast", False),
            help="Improve readability with high contrast colors"
        )
        st.session_state["high_contrast"] = high_contrast
    
    with col2:
        large_text = st.checkbox(
            "Large Text",
            value=st.session_state.get("large_text", False),
            help="Increase font size for easier reading"
        )
        st.session_state["large_text"] = large_text
    
    keyboard_nav = st.checkbox(
        "Keyboard Navigation Help",
        value=st.session_state.get("keyboard_nav_help", False),
        help="Show keyboard shortcuts on all pages"
    )
    st.session_state["keyboard_nav_help"] = keyboard_nav
    
    st.divider()
    
    st.markdown("### Data Display")
    
    col1, col2 = st.columns(2)
    
    with col1:
        show_advanced_metrics = st.checkbox(
            "Show Advanced Metrics",
            value=st.session_state.get("show_advanced", True)
        )
        st.session_state["show_advanced"] = show_advanced_metrics
    
    with col2:
        number_format = st.selectbox(
            "Number Format",
            options=["USD ($)", "Crypto (BTC)", "Percent (%)"],
            index=0
        )
        st.session_state["number_format"] = number_format

# ============================================================================
# TAB 4: EXPORT & BACKUP
# ============================================================================
with tab4:
    st.markdown("### Export Settings")
    
    # Create settings dict
    settings = {
        "risk": {
            "max_position_size": st.session_state.get("max_position_size", 0.10),
            "daily_loss_limit": st.session_state.get("daily_loss_limit", 1000),
            "min_confidence": st.session_state.get("min_confidence", 0.60),
            "max_trades_per_day": st.session_state.get("max_trades_per_day", 20),
            "max_concentration": st.session_state.get("max_concentration", 50),
            "drawdown_tolerance": st.session_state.get("drawdown_tolerance", 20),
        },
        "model": {
            "type": st.session_state.get("nova_model", "lite"),
            "temperature": st.session_state.get("nova_temperature", 0.7),
            "max_tokens": st.session_state.get("nova_max_tokens", 500),
        },
        "display": {
            "theme": st.session_state.get("theme", "dark"),
            "high_contrast": st.session_state.get("high_contrast", False),
            "large_text": st.session_state.get("large_text", False),
        },
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            label="📥 Download Settings (JSON)",
            data=json.dumps(settings, indent=2),
            file_name=f"protocol-zero-settings-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        uploaded_file = st.file_uploader(
            "📤 Upload Settings (JSON)",
            type=["json"],
            help="Import previously exported settings",
            key="settings_upload"
        )
        
        if uploaded_file:
            try:
                imported = json.load(uploaded_file)
                if st.button("Apply Imported Settings", use_container_width=True):
                    # Apply imported settings
                    if "risk" in imported:
                        for key, value in imported["risk"].items():
                            st.session_state[key] = value
                    if "model" in imported:
                        st.session_state["nova_model"] = imported["model"].get("type", "lite")
                        st.session_state["nova_temperature"] = imported["model"].get("temperature", 0.7)
                    if "display" in imported:
                        st.session_state["theme"] = imported["display"].get("theme", "dark")
                    st.success("✅ Settings imported successfully!")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file")
    
    with col3:
        if st.button("🔄 Reset to Defaults", use_container_width=True, key="reset_settings"):
            # Reset to defaults
            st.session_state["max_position_size"] = 0.10
            st.session_state["daily_loss_limit"] = 1000
            st.session_state["min_confidence"] = 0.60
            st.session_state["max_trades_per_day"] = 20
            st.session_state["nova_model"] = "lite"
            st.session_state["theme"] = "dark"
            st.success("✅ Settings reset to defaults")
    
    st.divider()
    
    st.markdown("### Settings Summary")
    st.json(settings)

# Footer
st.divider()
st.markdown("""
#### 💡 Tips
- **Conservative preset** is recommended for beginners and testing
- **Aggressive preset** requires active monitoring and robust AWS setup
- Export your settings for backup or sharing configurations
- Changes take effect immediately on all pages
""")
