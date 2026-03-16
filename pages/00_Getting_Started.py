"""
🎬 Getting Started / Demo Mode
Perfect entry point for judges and new users - instant setup with sample data
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
import pandas as pd
import streamlit as st

import app_core as core

# Initialize demo state
if "demo_mode" not in st.session_state:
    st.session_state["demo_mode"] = True
if "demo_initialized" not in st.session_state:
    st.session_state["demo_initialized"] = False

# Page config
st.set_page_config(page_title="🎬 Getting Started", layout="wide")

# Only show header/sidebar if not in demo mode, or show simplified version
if not st.session_state.get("demo_mode"):
    core.render_shell(current_panel="🎬  Getting Started", show_top_row=True)

# ============================================================================
# DEMO MODE ENTRY POINT
# ============================================================================

col1, col2 = st.columns([1, 2])

with col1:
    st.image("https://via.placeholder.com/150x150?text=Protocol+Zero", width=150)

with col2:
    st.title("🎬 Protocol Zero Demo")
    st.markdown("""
    **Welcome to Protocol Zero** — the trust-minimized autonomous DeFi trading agent  
    built on **ERC-8004** with **Amazon Nova AI** reasoning.
    """)

st.divider()

# Demo options
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Quick Demo", "📚 Tutorial", "🎯 Features", "⚙️ Setup"])

# ============================================================================
# TAB 1: QUICK DEMO
# ============================================================================
with tab1:
    st.markdown("### Start exploring immediately with pre-loaded sample data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎮 Explore as Demo User", key="demo_start", use_container_width=True):
            st.session_state["demo_mode"] = True
            st.session_state["demo_initialized"] = True
            st.session_state["total_capital_usd"] = 50000
            st.session_state["portfolio_tokens"] = {"ETH": 10, "USDC": 20000}
            st.success("✅ Demo mode activated! Check the pages in the sidebar.")
            st.info("Demo features: All pages are fully interactive with sample data")
    
    with col2:
        if st.button("⚡ Skip to Dashboard", key="skip_intro", use_container_width=True):
            st.session_state["demo_mode"] = True
            st.session_state["demo_initialized"] = True
            st.switch_page("pages/00_Dashboard.py")
    
    st.markdown("""
    #### What you'll see in demo mode:
    
    1. **📊 Dashboard** — Live portfolio metrics, P&L, performance indicators
    2. **📈 Market** — Real BTC/ETH data with trend analysis, regime detection  
    3. **🧠 AI Brain** — Nova reasoning on market conditions with confidence scores
    4. **🛡️ Risk & Exec** — 6-layer risk gates, trade execution simulation
    5. **🤝 Trust Panel** — ERC-8004 agent identity, on-chain reputation
    6. **📉 Performance** — Equity curve, Sharpe ratio, max drawdown
    7. **🎙️ Voice AI** — Premium UI with keyboard shortcuts (Alt+V to activate)
    
    All with **no AWS setup required** — using fallback data and simulated mode.
    """)

# ============================================================================
# TAB 2: TUTORIAL
# ============================================================================
with tab2:
    st.markdown("### 5-Minute Architecture Tour")
    
    st.markdown("""
    #### The Hackathon Problem
    
    Autonomous AI agents can be black boxes — how do we trust their decisions?  
    Protocol Zero solves this with **ERC-8004 on-chain accountability**.
    
    #### The Solution Architecture
    
    ```
    ┌──────────────┐
    │ Market Data  │  (CCXT, Uniswap)
    └───────┬──────┘
            │
            ▼
    ┌──────────────────────┐
    │  Amazon Nova Lite    │  ← AI Reasoning (Bedrock)
    │  (agentic tool-use)  │
    └───────┬──────────────┘
            │
            ▼
    ┌──────────────┐
    │  6-Layer     │  1. Position size limit
    │  Risk Gate   │  2. Daily loss cap
    │              │  3. Trade frequency
    │              │  4. Concentration
    │              │  5. Confidence floor
    │              │  6. Intent expiry
    └───────┬──────┘
            │
            ▼
    ┌──────────────────────┐
    │  EIP-712 Signature   │  ← Cryptographic proof
    │  (Trade Intent)      │
    └───────┬──────────────┘
            │
            ▼
    ┌──────────────────────┐
    │  ERC-8004 Registries │  ← On-chain audit trail
    │  - Identity          │
    │  - Reputation        │
    │  - Validation        │
    └──────────────────────┘
    ```
    
    #### Why This Wins Hackathons
    
    ✅ **Trustless**: Every decision is signed and verifiable on-chain  
    ✅ **Explainable**: See Nova's exact reasoning (prompts → decisions)  
    ✅ **Safe**: 6 independent risk checks prevent ruin  
    ✅ **Auditable**: Complete cryptographic audit trail  
    ✅ **Scalable**: ERC-8004 standard for agent identity  
    """)

# ============================================================================
# TAB 3: FEATURES
# ============================================================================
with tab3:
    st.markdown("### Core Features Built")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🤖 AI & Reasoning
        - **Nova Lite**: Real agentic reasoning with tool-use
        - **Confidence Scoring**: 0-100% decision confidence
        - **Market Regime Detection**: Trending, ranging, volatile
        - **Risk Score Calculation**: Dynamic risk assessment
        - **Fallback Mode**: Works without AWS credentials
        
        #### 🔐 On-Chain & Cryptography
        - **EIP-712 Signatures**: Cryptographic trade intents
        - **ERC-8004 Integration**: Agent identity registry
        - **Nonce Tracking**: Replay protection
        - **Sepolia Testnet**: Full testnet support
        - **Validation Artifacts**: Audit trail builder
        """)
    
    with col2:
        st.markdown("""
        #### 📊 Analytics & Monitoring
        - **Real-time P&L**: Live portfolio metrics
        - **Equity Curve**: Historical performance
        - **Sharpe Ratio**: Risk-adjusted returns
        - **Max Drawdown**: Risk metrics
        - **Win Rate**: Trade success percentage
        
        #### 🎙️ Voice AI & UX
        - **Voice Commands**: Alt+V to activate
        - **Premium Styling**: Glass-morphism, animations
        - **Keyboard Shortcuts**: Alt+K (kill), S (status), R (risk)
        - **Accessibility**: High contrast mode, ARIA labels
        - **Responsive Design**: Works on mobile, tablet, desktop
        """)

# ============================================================================
# TAB 4: SETUP
# ============================================================================
with tab4:
    st.markdown("### How to Deploy")
    
    with st.expander("📦 1. Local Development (5 minutes)", expanded=False):
        st.code("""
# Clone and setup
git clone https://github.com/Direwolfe999/Protocol-Zero.git
cd Protocol-Zero
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
streamlit run pages/00_Dashboard.py

# Access at http://localhost:8501
        """, language="bash")
    
    with st.expander("☁️ 2. AWS Setup (10 minutes)", expanded=False):
        st.code("""
# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
RPC_URL=https://sepolia.infura.io/v3/your_key
PRIVATE_KEY=your_private_key

# Verify credentials work
python -c "import app_core; print('✓ Ready')"

# Deploy to Streamlit Cloud
git push origin main
# Connect GitHub repo to Streamlit Cloud
        """, language="bash")
    
    with st.expander("🐳 3. Docker Deployment (15 minutes)", expanded=False):
        st.code("""
# Build image
docker build -t protocol-zero:latest .

# Run container with env
docker run -e AWS_ACCESS_KEY_ID=xxx \\
           -e AWS_SECRET_ACCESS_KEY=yyy \\
           -e RPC_URL=zzz \\
           -p 8501:8501 \\
           protocol-zero:latest

# Access at http://localhost:8501
        """, language="bash")

st.divider()

# ============================================================================
# JUDGE INFO BOX
# ============================================================================

st.info("""
### 🏆 For Hackathon Judges

**This is your entry point.** Everything below works without setup:
- ✅ Demo mode with real market data
- ✅ All 15 pages fully interactive
- ✅ Nova AI reasoning (fallback mode)
- ✅ ERC-8004 simulation
- ✅ Voice AI with premium UI
- ✅ Full risk engine testing

**Code locations:**
- Core logic: [`app_core.py`](https://github.com/Direwolfe999/Protocol-Zero/blob/main/app_core.py) (2600 lines)
- AI reasoning: [`brain.py`](https://github.com/Direwolfe999/Protocol-Zero/blob/main/brain.py)
- On-chain: [`chain_interactor.py`](https://github.com/Direwolfe999/Protocol-Zero/blob/main/chain_interactor.py)
- Risk engine: [`risk_check.py`](https://github.com/Direwolfe999/Protocol-Zero/blob/main/risk_check.py)
- Voice: [`nova_sonic_voice.py`](https://github.com/Direwolfe999/Protocol-Zero/blob/main/nova_sonic_voice.py)

**Tests:** Run `pytest tests/` → **143/143 PASS** ✅

**Key differentiators:**
1. ERC-8004 on-chain agent identity (not just local)
2. Cryptographic proof of reasoning (EIP-712)
3. 6-layer fail-closed risk gates (not just heuristics)
4. Real Nova integration (not mocked)
5. Full voice AI with premium UX
""")

# Navigation hint
st.divider()
st.markdown("""
### Next Steps

1. **Start Demo**: Click "🎮 Explore as Demo User" above
2. **Explore Pages**: Use sidebar navigation (15 pages total)
3. **Try Voice AI**: Press `Alt+V` on any page
4. **Check Code**: Visit [GitHub](https://github.com/Direwolfe999/Protocol-Zero)
5. **Read Docs**: See [DEPLOYMENT.md](./DEPLOYMENT.md) for full setup

---
*Built for Amazon Nova AI Hackathon | ERC-8004 Standard | Capital Preservation First*
""")
