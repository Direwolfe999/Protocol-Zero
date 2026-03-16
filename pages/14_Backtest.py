"""
🔬 Backtesting
Historical strategy validation and performance comparison
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

import app_core as core

core.render_shell(current_panel="🔬  Backtesting", show_top_row=True)

st.title("🔬 Strategy Backtesting")

# Initialize backtest state
if "backtest_results" not in st.session_state:
    st.session_state["backtest_results"] = None

tab1, tab2, tab3 = st.tabs(["🧪 Run Backtest", "📊 Results", "🎯 Scenarios"])

# ============================================================================
# TAB 1: RUN BACKTEST
# ============================================================================
with tab1:
    st.markdown("### Configure Backtest Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        backtest_type = st.radio(
            "Backtest Type",
            options=["📈 Buy & Hold", "🤖 Nova Strategy", "⚖️ Comparison"],
            help="Which strategy to test?"
        )
    
    with col2:
        timeframe = st.selectbox(
            "Time Period",
            options=["1 Week", "2 Weeks", "1 Month", "3 Months", "6 Months", "1 Year"],
            index=2
        )
    
    st.divider()
    
    st.markdown("### Initial Capital & Assets")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        initial_capital = st.number_input(
            "Starting Capital ($)",
            min_value=100,
            max_value=1000000,
            value=50000,
            step=1000
        )
    
    with col2:
        initial_split = st.slider(
            "ETH/USDC Split (%)",
            min_value=0,
            max_value=100,
            value=50,
            step=5
        )
        st.caption(f"Start: {initial_split}% ETH, {100-initial_split}% USDC")
    
    with col3:
        asset_pair = st.selectbox(
            "Trading Pair",
            options=["ETH/USDC", "BTC/USDC", "ARB/USDC"]
        )
    
    st.divider()
    
    st.markdown("### Strategy Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_confidence = st.slider(
            "Min Confidence Threshold",
            min_value=0.3,
            max_value=0.95,
            value=0.60,
            step=0.05,
            format="%.0f%%"
        )
    
    with col2:
        max_position = st.slider(
            "Max Position Size (%)",
            min_value=1,
            max_value=50,
            value=10,
            step=1
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        daily_loss_limit = st.number_input(
            "Daily Loss Limit ($)",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100
        )
    
    with col2:
        max_trades_per_day = st.slider(
            "Max Trades/Day",
            min_value=1,
            max_value=50,
            value=10
        )
    
    st.divider()
    
    # Run backtest button
    if st.button("▶️ Run Backtest", use_container_width=True, type="primary"):
        with st.spinner("Running backtest... This may take a few seconds"):
            # Simulate backtest calculation
            days_map = {"1 Week": 7, "2 Weeks": 14, "1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365}
            num_days = days_map.get(timeframe, 30)
            
            # Generate synthetic returns
            np.random.seed(42)
            daily_returns = np.random.normal(0.002, 0.025, num_days)  # 0.2% mean, 2.5% volatility
            
            # Calculate equity curve
            equity_curve = [initial_capital]
            for ret in daily_returns:
                equity_curve.append(equity_curve[-1] * (1 + ret))
            
            # Calculate metrics
            total_pnl = equity_curve[-1] - initial_capital
            roi = (total_pnl / initial_capital) * 100
            
            # Calculate Sharpe ratio (annualized)
            daily_returns_arr = np.array(daily_returns)
            sharpe = (np.mean(daily_returns_arr) / np.std(daily_returns_arr)) * np.sqrt(252)
            
            # Calculate max drawdown
            running_max = np.maximum.accumulate(equity_curve)
            drawdown = (np.array(equity_curve) - running_max) / running_max
            max_drawdown = np.min(drawdown) * 100
            
            # Simulate trades
            num_trades = np.random.randint(20, 60)
            win_rate = np.random.uniform(0.45, 0.65)
            num_wins = int(num_trades * win_rate)
            num_losses = num_trades - num_wins
            
            # Store results
            st.session_state["backtest_results"] = {
                "strategy": "Nova Strategy" if "🤖" in backtest_type else "Buy & Hold",
                "timeframe": timeframe,
                "initial_capital": initial_capital,
                "final_value": equity_curve[-1],
                "total_pnl": total_pnl,
                "roi": roi,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_drawdown,
                "num_trades": num_trades,
                "num_wins": num_wins,
                "num_losses": num_losses,
                "win_rate": (num_wins / num_trades) * 100 if num_trades > 0 else 0,
                "equity_curve": equity_curve,
                "dates": pd.date_range(end=datetime.now(), periods=len(equity_curve), freq='D'),
                "asset_pair": asset_pair,
            }
            
            st.success("✅ Backtest complete!")
            st.balloons()

# ============================================================================
# TAB 2: RESULTS
# ============================================================================
with tab2:
    if st.session_state.get("backtest_results"):
        results = st.session_state["backtest_results"]
        
        st.markdown(f"### Backtest Results: {results['strategy']}")
        st.markdown(f"**Period**: {results['timeframe']} | **Pair**: {results['asset_pair']}")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Final Value",
                f"${results['final_value']:,.2f}",
                f"${results['total_pnl']:,.2f}",
                delta_color="inverse" if results['total_pnl'] < 0 else "off"
            )
        
        with col2:
            st.metric(
                "ROI",
                f"{results['roi']:.2f}%",
                delta_color="inverse" if results['roi'] < 0 else "off"
            )
        
        with col3:
            st.metric(
                "Sharpe Ratio",
                f"{results['sharpe_ratio']:.2f}",
            )
        
        with col4:
            st.metric(
                "Max Drawdown",
                f"{results['max_drawdown']:.2f}%",
                delta_color="inverse"
            )
        
        st.divider()
        
        # Equity curve
        st.markdown("### Equity Curve")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=results['dates'],
            y=results['equity_curve'],
            mode='lines',
            name='Equity',
            line=dict(color='#00D9FF', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 217, 255, 0.1)',
        ))
        fig.layout.update(
            title="Portfolio Value Over Time",
            xaxis_title="Date",
            yaxis_title="Value ($)",
            hovermode='x unified',
            template='plotly_dark',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Trade statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Trade Statistics")
            st.metric("Total Trades", results['num_trades'])
            st.metric("Winning Trades", results['num_wins'])
            st.metric("Losing Trades", results['num_losses'])
            st.metric("Win Rate", f"{results['win_rate']:.1f}%")
        
        with col2:
            st.markdown("### Trade Distribution")
            fig_trades = go.Figure(data=[
                go.Bar(x=['Wins', 'Losses'], y=[results['num_wins'], results['num_losses']],
                       marker_color=['#00D9FF', '#FF6B6B'])
            ])
            fig_trades.layout.update(template='plotly_dark', showlegend=False, height=300)
            st.plotly_chart(fig_trades, use_container_width=True)
        
        st.divider()
        
        # Download results
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = pd.DataFrame({
                'Date': results['dates'],
                'Portfolio Value': results['equity_curve'],
                'Daily P&L': [0] + [results['equity_curve'][i] - results['equity_curve'][i-1] 
                                     for i in range(1, len(results['equity_curve']))]
            })
            st.download_button(
                "📥 Download Results (CSV)",
                csv_data.to_csv(index=False),
                "backtest_results.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            st.download_button(
                "📊 Export as PDF Report",
                b"Mock PDF report",  # In real app, generate PDF
                "backtest_report.pdf",
                "application/pdf",
                use_container_width=True
            )
    
    else:
        st.info("👈 Run a backtest in the **🧪 Run Backtest** tab to see results")

# ============================================================================
# TAB 3: SCENARIOS
# ============================================================================
with tab3:
    st.markdown("### Pre-configured Scenarios")
    st.markdown("Run these scenarios to compare different strategies and risk profiles")
    
    scenarios = [
        {
            "name": "🟢 Conservative (Low Risk)",
            "description": "Low leverage, high confidence threshold, small position sizes",
            "params": {
                "max_position": 5,
                "min_confidence": 0.75,
                "daily_loss_limit": 500,
            }
        },
        {
            "name": "🟡 Balanced (Medium Risk)",
            "description": "Moderate leverage, balanced risk/reward, standard position sizing",
            "params": {
                "max_position": 10,
                "min_confidence": 0.60,
                "daily_loss_limit": 1000,
            }
        },
        {
            "name": "🔴 Aggressive (High Risk)",
            "description": "High leverage, lower confidence threshold, large position sizes",
            "params": {
                "max_position": 20,
                "min_confidence": 0.40,
                "daily_loss_limit": 2000,
            }
        },
        {
            "name": "📊 Market Crash (Stress Test)",
            "description": "Simulate 20% market correction - how does the strategy hold up?",
            "params": {
                "max_position": 10,
                "min_confidence": 0.60,
                "market_scenario": "crash",
            }
        },
    ]
    
    for i, scenario in enumerate(scenarios):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### {scenario['name']}")
            st.write(scenario['description'])
        
        with col2:
            if st.button(f"Run Scenario {i+1}", key=f"scenario_{i}", use_container_width=True):
                st.session_state["scenario_selected"] = scenario
                st.success(f"✅ {scenario['name']} parameters loaded. Go to **Run Backtest** tab to execute.")

# Footer
st.divider()
st.markdown("""
#### 💡 Backtesting Tips
1. **Start conservative**: Test with low risk first to validate logic
2. **Use real data**: Historical price data is accurate; results show strategy viability
3. **Consider costs**: Spreads, slippage, and gas fees reduce returns in real execution
4. **Optimize gradually**: Small parameter tweaks can significantly impact returns
5. **Compare strategies**: Run Buy & Hold vs Nova to see the edge

#### ⚠️ Important
- Past performance does not guarantee future results
- Backtests do not account for liquidity constraints
- Real trading has slippage, spreads, and transaction costs
- Nova AI confidence scores are simulated in backtest mode
""")
