"""
Protocol Zero — Getting Started & Demo Mode
=============================================
Demo-friendly entry point for judges and first-time users.
No AWS credentials required — uses pre-loaded sample data.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

import app_core as core


# ─────────────────────────────────────────────────────────────
# DEMO MODE INITIALIZATION
# ─────────────────────────────────────────────────────────────

def _init_demo_session():
    """Initialize demo mode session state."""
    if "demo_mode" not in st.session_state:
        st.session_state["demo_mode"] = True
        st.session_state["demo_portfolio_value"] = 25_000.0
        st.session_state["demo_session_pnl"] = 1_247.50
        st.session_state["demo_trades_count"] = 12
        st.session_state["demo_win_rate"] = 0.67
        st.session_state["demo_sharpe"] = 1.85
        st.session_state["demo_max_drawdown"] = 0.08


def _get_demo_market_data() -> pd.DataFrame:
    """Generate realistic demo market data (ETH/USDT, last 72 hours)."""
    now = datetime.now(timezone.utc)
    hours = pd.date_range(end=now, periods=72, freq='1h')
    
    # Realistic price movement
    base_price = 1850.0
    prices = [base_price]
    for i in range(1, len(hours)):
        change = (i % 12 - 6) * 15 + (i % 7 - 3) * 10  # Realistic volatility
        prices.append(base_price + change + (i * 5))
    
    volumes = [pd.Series(prices).rolling(window=3).std().mean() * 10000 * (0.8 + (i % 5) * 0.1) 
               for i in range(len(hours))]
    
    df = pd.DataFrame({
        'timestamp': hours,
        'open': prices,
        'high': [p + 25 for p in prices],
        'low': [p - 15 for p in prices],
        'close': prices,
        'volume': volumes,
    })
    
    return df.set_index('timestamp')


def _get_demo_trades() -> list[dict]:
    """Get sample trade history."""
    return [
        {"action": "BUY", "asset": "ETH", "amount": 5.2, "price": 1825, "pnl": 145.50, "timestamp": "14:32:01"},
        {"action": "SELL", "asset": "ETH", "amount": 3.1, "price": 1880, "pnl": 98.25, "timestamp": "13:15:45"},
        {"action": "BUY", "asset": "ETH", "amount": 4.0, "price": 1840, "pnl": 220.00, "timestamp": "11:48:20"},
        {"action": "HOLD", "asset": "ETH", "amount": 0.0, "price": 1860, "pnl": 0.0, "timestamp": "10:20:11"},
        {"action": "SELL", "asset": "ETH", "amount": 2.5, "price": 1895, "pnl": 185.75, "timestamp": "09:05:33"},
    ]


# ─────────────────────────────────────────────────────────────
# DEMO CONTENT SECTIONS
# ─────────────────────────────────────────────────────────────

def render_welcome():
    """Render welcome hero section."""
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #0a0a2e 0%, #1a0a3e 100%); 
    border-radius: 12px; margin-bottom: 30px;">
        <h1 style="margin: 0; color: #00ff88; font-size: 2.5em;">🛡️ Protocol Zero</h1>
        <h2 style="margin: 10px 0 0 0; color: #00ccff; font-size: 1.3em;">Autonomous DeFi Trading Agent</h2>
        <p style="margin-top: 20px; color: #aaa; font-size: 1.1em; max-width: 600px; margin-left: auto; margin-right: auto;">
            <strong>Powered by Amazon Nova AI</strong> • On-chain ERC-8004 compliance • 6-layer risk pipeline • 
            Cryptographic intent signing (EIP-712)
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_quick_facts():
    """Render key facts about the project."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🧠 Nova AI Models", "4", help="Lite (reasoning) + Voice + Act + Embeddings")
    with col2:
        st.metric("📊 Dashboard Pages", "15", help="Specialized analysis and control pages")
    with col3:
        st.metric("🛡️ Risk Checks", "6", help="Multi-layer fail-closed safety pipeline")
    with col4:
        st.metric("⛓️ On-Chain", "ERC-8004", help="Identity + Reputation + Validation registries")


def render_demo_portfolio():
    """Render demo portfolio metrics."""
    st.subheader("📈 Demo Portfolio (ETH/USDT)")
    
    _init_demo_session()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "💰 Portfolio Value",
            f"${st.session_state['demo_portfolio_value']:,.0f}",
            f"+${st.session_state['demo_session_pnl']:,.2f}",
            delta_color="off"
        )
    with col2:
        st.metric(
            "📊 Total Trades",
            st.session_state['demo_trades_count'],
            help="Number of trades this session"
        )
    with col3:
        st.metric(
            "✅ Win Rate",
            f"{st.session_state['demo_win_rate']:.1%}",
            f"+{int(st.session_state['demo_win_rate'] * st.session_state['demo_trades_count'])} wins"
        )
    with col4:
        st.metric(
            "📈 Sharpe Ratio",
            f"{st.session_state['demo_sharpe']:.2f}",
            help="Risk-adjusted returns"
        )
    with col5:
        st.metric(
            "📉 Max Drawdown",
            f"{st.session_state['demo_max_drawdown']:.1%}",
            help="Largest peak-to-trough decline"
        )


def render_nova_integration():
    """Showcase Nova AI integration."""
    st.subheader("🧠 Amazon Nova AI — 4 Integration Points")
    
    tabs = st.tabs(["Nova Lite", "Nova Voice", "Nova Act", "Nova Embeddings"])
    
    with tabs[0]:
        st.markdown("""
        **Nova Lite — Agentic Market Reasoning**
        - Analyzes OHLCV market data with reasoning
        - Tool-use loop: can request rug-pull scans, contract audits, embedding analysis
        - Confidence scoring: only trades when conviction is high
        - Real Bedrock Converse API integration
        """)
        col1, col2 = st.columns(2)
        with col1:
            st.code("""
# Example Nova decision
{
  "action": "BUY",
  "asset": "ETH",
  "amount_usd": 500,
  "confidence": 0.87,
  "reason": "RSI oversold + bullish crossover"
}
            """, language="json")
    
    with tabs[1]:
        st.markdown("""
        **Nova Voice — Voice Commands + Text Intelligence**
        - "What is my risk exposure?" → Spoken response
        - "Emergency stop" → Kill switch activation
        - Real Nova Lite Converse API for intelligent responses
        - Browser Web Speech API for TTS
        """)
        st.code("""
Command: "Protocol Zero, what is my balance?"
Response: "Your portfolio is currently valued at 
25,000 USD. No active positions. Ready for trading."
        """, language="text")
    
    with tabs[2]:
        st.markdown("""
        **Nova Act — Smart Contract Auditing**
        - Browser-based contract verification
        - Scam pattern detection
        - Integration ready for AWS provisioning
        - Used in the agentic tool-use loop
        """)
        st.info("⚠️ Nova Act audit results are currently simulated.\nUnlock with AWS credentials in Settings.")
    
    with tabs[3]:
        st.markdown("""
        **Nova Embeddings — Multimodal Scam Detection**
        - Cosine similarity analysis on token metadata
        - Detects rug-pull indicators
        - Real embedding model when AWS configured
        - Heuristic fallback when unavailable
        """)
        st.success("✅ Embeddings analysis ready for live tokens")


def render_features():
    """Showcase key features."""
    st.subheader("✨ Core Features")
    
    feat_cols = st.columns(3)
    
    features = [
        ("🎯 15-Page Dashboard", "Specialized pages for market analysis, risk management, voice commands, backtesting"),
        ("🛡️ 6-Layer Risk Pipeline", "Position size • Daily loss • Frequency • Concentration • Confidence • Expiry"),
        ("✍️ EIP-712 Signing", "Cryptographic intent signing — AI never touches private keys"),
        ("🔗 ERC-8004 On-Chain", "Agent identity, reputation scores, and validation artifacts registered on-chain"),
        ("📊 Real Market Data", "Live OHLCV data from CCXT (Binance, Kraken, Coinbase)"),
        ("🎙️ Voice AI", "Voice commands + streaming responses + premium UI"),
    ]
    
    for idx, (title, desc) in enumerate(features):
        with feat_cols[idx % 3]:
            st.markdown(f"**{title}**\n\n{desc}")


def render_how_it_works():
    """Explain the decision loop."""
    st.subheader("⚙️ How Protocol Zero Works")
    
    st.markdown("""
    ```
    ┌──────────┐     ┌─────────┐     ┌──────────────┐     ┌───────────────┐
    │ Fetch    │ ──► │  Brain  │ ──► │ Risk Check   │ ──► │ Validate +    │
    │ Market   │     │ (Nova)  │     │ (6 checks)   │     │ Sign (EIP712) │
    │ Data     │     │         │     │              │     │               │
    └──────────┘     └─────────┘     └──────────────┘     └───────┬───────┘
                                                                  │
                        ┌─────────────────────────────────────────┤
                        ▼                                         ▼
                 ┌──────────────┐                 ┌───────────────────┐
                 │ Validation   │                 │ Reputation        │
                 │ Artifacts    │                 │ (giveFeedback)    │
                 └──────────────┘                 └───────────────────┘
    ```
    
    1. **Fetch Market Data** — Real-time OHLCV from CCXT
    2. **Brain Decides** — Nova Lite analyzes + tool-use loop
    3. **Risk Gates** — 6 independent checks (fail-closed)
    4. **Sign Intent** — EIP-712 cryptographic validation
    5. **Log On-Chain** — Register in ERC-8004 Validation Registry
    """)


def render_demo_trades():
    """Show demo trades."""
    st.subheader("📜 Demo Trade History")
    
    trades = _get_demo_trades()
    df = pd.DataFrame(trades)
    
    st.dataframe(
        df.style.applymap(
            lambda x: "background-color: #1a3a1a" if isinstance(x, str) and x == "BUY" 
            else ("background-color: #3a1a1a" if isinstance(x, str) and x == "SELL" else ""),
            subset=["action"]
        ),
        use_container_width=True,
        hide_index=True
    )


def render_cta():
    """Call to action."""
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 40px;">
        <h3>Ready to Explore?</h3>
        <p>Navigate using the sidebar to explore all 15 pages of Protocol Zero.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Dashboard →", use_container_width=True):
            st.switch_page("pages/00_Dashboard.py")
    
    with col2:
        if st.button("📈 Market Data →", use_container_width=True):
            st.switch_page("pages/01_Market.py")
    
    with col3:
        if st.button("🧠 AI Brain →", use_container_width=True):
            st.switch_page("pages/02_AI_Brain.py")
    
    with col4:
        if st.button("🎙️ Voice AI →", use_container_width=True):
            st.switch_page("pages/13_Voice_AI.py")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(
        page_title="Protocol Zero — Getting Started",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom styling
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8em; }
    </style>
    """, unsafe_allow_html=True)
    
    # Demo mode banner
    st.warning("🎮 **DEMO MODE** — No AWS credentials needed. Explore with pre-loaded sample data.")
    
    # Render sections
    render_welcome()
    render_quick_facts()
    
    st.markdown("---")
    
    render_demo_portfolio()
    
    st.markdown("---")
    
    render_nova_integration()
    
    st.markdown("---")
    
    render_features()
    
    st.markdown("---")
    
    render_how_it_works()
    
    st.markdown("---")
    
    render_demo_trades()
    
    render_cta()
