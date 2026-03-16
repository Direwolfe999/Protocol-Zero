from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_risk_execution_panel(
    *,
    df: pd.DataFrame,
    run_analysis: Callable[[pd.DataFrame, str, float], dict[str, Any]],
    mcard: Callable[..., str],
    risk_heatmap_html: Callable[[dict[str, Any], Any, float], str],
    risk_router_html: Callable[[Any], str],
    simulate_trade: Callable[[dict[str, Any], float], dict[str, Any]],
    cog: Callable[[str, str, str], None],
    real_execute_trade: Callable[[dict[str, Any], pd.DataFrame], dict[str, Any]],
    has_chain: bool,
    chain_obj: Any,
    logger: Any,
) -> None:
    st.markdown("### 🛡️ Risk Management & Execution")

    # ── Risk Heat Map ─────────────────────────────────────
    st.markdown("#### ⚖️ Risk Heat Map")
    st.markdown(risk_heatmap_html(
        dict(st.session_state),
        st.session_state.get("latest_decision"),
        st.session_state["whatif_vol_mult"],
    ), unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Risk Router Map ─────────────────────────────────
    st.markdown("#### 🛡️ Risk Router — Rug-Pull Check Pipeline")
    st.caption("Visual flowchart of how the AI validates tokens before trading.")
    st.markdown(risk_router_html(st.session_state.get("latest_decision")),
                unsafe_allow_html=True)

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Transaction Simulator ───────────────────────────
    st.markdown("#### 🧪 Transaction Simulator")
    st.caption("Dry-run the trade locally — see expected gas and final balance before spending real Coins.")
    sim_dec = st.session_state.get("latest_decision")
    if sim_dec and sim_dec["action"] != "HOLD":
        if st.button("🧪  Simulate Trade", use_container_width=True):
            sim = simulate_trade(sim_dec, st.session_state["total_capital_usd"])
            cog("🧪", f"Simulation: gas={sim['gas_gwei']}gwei "
                f"slip={sim['slippage_pct']}% net=${sim['net_amount']}", "info")
            st.markdown(f"""
            <div class="sim-result">
                <div style="color:#4fc3f7;font-weight:600;font-size:0.75rem;
                            margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:1px">
                    🧪 Simulation Results</div>
                <div class="sim-row">
                    <span style="color:#8892b0">Gas Price</span>
                    <span style="color:#ccd6f6">{sim['gas_gwei']} gwei</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Gas Cost</span>
                    <span style="color:#ccd6f6">{sim['gas_cost_eth']:.6f} ETH (${sim['gas_cost_usd']:.2f})</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Slippage</span>
                    <span style="color:#ffd93d">{sim['slippage_pct']:.2f}%</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Net Trade Amount</span>
                    <span style="color:#64ffda">${sim['net_amount']:,.2f}</span></div>
                <div class="sim-row">
                    <span style="color:#8892b0">Total Cost</span>
                    <span style="color:#ccd6f6">${sim['total_cost']:,.2f}</span></div>
                <div class="sim-row" style="border-top:1px solid #1a1a3e;padding-top:0.5rem;margin-top:0.3rem">
                    <span style="color:#8892b0;font-weight:600">Final Balance</span>
                    <span style="color:{'#64ffda' if sim['final_balance'] > 0 else '#ff6b6b'};font-weight:700">
                        ${sim['final_balance']:,.2f}</span></div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Run AI Analysis first to simulate a trade.")

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── What-If Volatility Simulator ──────────────────────
    st.markdown("#### 🔮 What-If Volatility Simulator")
    st.caption("Slide to simulate volatility changes and observe agent adaptation.")

    vol_mult = st.slider(
        "Volatility Multiplier",
        min_value=0.5, max_value=3.0,
        value=st.session_state["whatif_vol_mult"],
        step=0.1, key="whatif_slider",
        help="1.0 = current conditions. Higher = more volatile market simulation.",
    )
    st.session_state["whatif_vol_mult"] = vol_mult

    if vol_mult != 1.0:
        sim_dec = run_analysis(df, st.session_state["selected_pair"], vol_mult)
        sim_regime = sim_dec["market_regime"]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(mcard("Sim Regime", sim_regime), unsafe_allow_html=True)
        with c2:
            st.markdown(mcard("Sim Confidence", f"{sim_dec['confidence']:.0%}",
                              "", sim_dec["confidence"] >= 0.6), unsafe_allow_html=True)
        with c3:
            st.markdown(mcard("Sim Position", f"{sim_dec['position_size_percent']:.1f}%",
                              "", sim_dec["position_size_percent"] > 0), unsafe_allow_html=True)
        with c4:
            st.markdown(mcard("Sim Risk", f"{sim_dec['risk_score']}/10",
                              "", sim_dec["risk_score"] <= 5), unsafe_allow_html=True)

        if (sim_dec["action"] == "HOLD"
                and (st.session_state.get("latest_decision") or {}).get("action") != "HOLD"):
            st.warning("🔮 At this volatility, the agent would **HOLD** instead of "
                       "trading. Risk-adaptive behavior confirmed.")
    else:
        st.info("Move the slider to simulate different volatility scenarios.")

    st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

    # ── Pre-flight checks + execute ───────────────────────
    dec = st.session_state.get("latest_decision")
    if dec and dec["action"] != "HOLD":
        st.markdown("#### Pre-Flight Risk Checks")

        max_pos = st.session_state["max_position_usd"]
        _rep = st.session_state.get("reputation_score", 95)
        _risk_s = dec.get("risk_score", 5)

        checks: list[tuple[str, bool, str]] = [
            ("Position ≤ 2% Capital",
             dec["position_size_percent"] <= 2.0,
             f"{dec['position_size_percent']:.1f}% ≤ 2.0%"),
            ("Amount ≤ Max Position",
             dec["amount_usd"] <= max_pos,
             f"${dec['amount_usd']:.0f} ≤ ${max_pos:.0f}"),
            ("Daily Loss Limit",
             st.session_state["session_pnl"] > -st.session_state["max_daily_loss_usd"],
             f"PnL ${st.session_state['session_pnl']:+.2f} > "
             f"-${st.session_state['max_daily_loss_usd']:.0f}"),
            ("Confidence ≥ 40%",
             dec["confidence"] >= 0.4,
             f"{dec['confidence']:.0%} ≥ 40%"),
            ("ERC-8004 Reputation ≥ 30%",
             _rep >= 30,
             f"Rep {_rep}% ≥ 30%"),
            ("Risk Score ≤ 8/10",
             _risk_s <= 8,
             f"Risk {_risk_s}/10 ≤ 8/10"),
            ("Stop Loss Set",
             dec["stop_loss_percent"] > 0,
             f"SL = {dec['stop_loss_percent']:.1f}%"),
            ("Take Profit Set",
             dec["take_profit_percent"] > 0,
             f"TP = {dec['take_profit_percent']:.1f}%"),
            ("Trade Frequency",
             st.session_state["trade_count"] < 10,
             f"{st.session_state['trade_count']} < 10/session"),
            ("No Leverage", True, "Leverage: None"),
        ]
        all_passed = all(c[1] for c in checks)

        for name, passed, detail in checks:
            icon = "✅" if passed else "❌"
            c = "#64ffda" if passed else "#ff6b6b"
            st.markdown(f'<span style="color:{c}">{icon} **{name}**: {detail}</span>',
                        unsafe_allow_html=True)

        st.markdown('<div class="hz"></div>', unsafe_allow_html=True)

        if not all_passed:
            st.error("⛔ Risk checks failed — execution blocked.")

        if st.session_state["kill_switch_active"]:
            st.error("⛔ Kill switch is ACTIVE — all trading halted.")

        auto_mode = st.session_state["autonomous_mode"]

        if auto_mode and all_passed:
            if st.session_state["kill_switch_active"]:
                execute = False
            else:
                st.markdown("""
                <div class="auto-badge-on" style="margin-bottom:1rem">
                    <div style="font-size:0.9rem;font-weight:700;color:#64ffda">
                        ⚡ AUTO-EXECUTING…</div>
                </div>""", unsafe_allow_html=True)
                execute = True
        else:
            execute = st.button("🔏  Sign & Execute Trade",
                                use_container_width=True, type="primary",
                                disabled=(not all_passed
                                          or st.session_state["kill_switch_active"]))

        if execute and all_passed:
            with st.spinner("EIP-712 signing · Risk validation · On-chain broadcast…"):
                cog("▣", f"Signing EIP-712 TradeIntent: "
                    f"{dec['action']} {dec['asset']}", "info")

                exec_result = real_execute_trade(dec, df)

                if exec_result["sig"]:
                    sig = exec_result["sig"]
                    cog("▣", f"Signature: {str(sig)[:22]}…", "sym")
                else:
                    sig = "0x" + hashlib.sha256(
                        json.dumps(dec, default=str).encode()).hexdigest()[:64]
                    cog("▣", f"Local signature: {sig[:22]}…", "sym")

                if exec_result["tx"]:
                    tx = str(exec_result["tx"])
                    cog("✓", f"TX confirmed on-chain: {tx[:22]}…", "ok")
                else:
                    tx = "0x" + hashlib.sha256(
                        (str(sig) + str(time.time())).encode()).hexdigest()[:64]
                    if exec_result.get("error"):
                        cog("⚠", f"Chain: {exec_result['error']}", "warn")
                    cog("▣", f"Local TX ref: {tx[:22]}…", "sym")

                swap_info = exec_result.get("swap")
                if swap_info and isinstance(swap_info, dict):
                    st.session_state["last_swap_result"] = swap_info
                    if swap_info.get("success"):
                        cog("💱", f"DEX Swap SUCCESS: "
                            f"{swap_info.get('amount_in', 0):.6f} {swap_info.get('token_in', '?')}"
                            f" → {swap_info.get('amount_out', 0):.6f} {swap_info.get('token_out', '?')}", "ok")
                        cog("⛽", f"Gas used: {swap_info.get('gas_used', 0)} | "
                            f"Gas cost: {swap_info.get('gas_cost_eth', 0):.6f} ETH", "info")
                        stx = swap_info.get("tx_hash", "")
                        if stx:
                            cog("🔗", f"Etherscan: https://sepolia.etherscan.io/tx/{stx}", "ok")
                    else:
                        cog("❌", f"DEX Swap FAILED: {swap_info.get('error', 'unknown')}", "err")
                elif exec_result.get("swap_error"):
                    cog("⚠", f"DEX: {exec_result['swap_error']}", "warn")

                if exec_result.get("risk_report"):
                    cog("▣", "Risk report generated", "ok")

                _recent_ret = float(df["pct_change"].dropna().tail(5).mean()) if len(df) > 5 else 0.0
                _trade_amt = dec.get("amount_usd", 100.0)
                if dec["action"] == "BUY":
                    pnl = round(_trade_amt * _recent_ret / 100.0, 2)
                elif dec["action"] == "SELL":
                    pnl = round(_trade_amt * -_recent_ret / 100.0, 2)
                else:
                    pnl = 0.0
                _cap = _trade_amt * 0.05
                pnl = max(-_cap, min(_cap, pnl))
                st.session_state["session_pnl"] += pnl
                st.session_state["trade_count"] += 1

                if has_chain and chain_obj is not None:
                    try:
                        chain_obj.log_trade_result(
                            action_type=dec.get("action", "HOLD"),
                            pnl_bps=int(pnl * 100),
                            metadata=json.dumps({"pnl_usd": pnl, "asset": dec.get("asset", "")}),
                        )
                        cog("▣", "Reputation feedback submitted on-chain", "ok")
                    except Exception as e:
                        logger.warning("Reputation feedback failed: %s", e)

                st.session_state["reputation_score"] = max(
                    0, min(100, st.session_state["reputation_score"]
                           + (1 if pnl > 0 else -2)))

                st.session_state["calibration_data"].append({
                    "predicted_conf": dec["confidence"],
                    "actual_outcome": 1 if pnl > 0 else 0,
                    "pnl": pnl,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                cog("▣",
                    f"PnL: ${pnl:+.2f} — Reputation: "
                    f"{st.session_state['reputation_score']}",
                    "ok" if pnl > 0 else "warn")

                _swap_data = exec_result.get("swap")
                _dex_label = ""
                if _swap_data and isinstance(_swap_data, dict) and _swap_data.get("success"):
                    _dex_label = " + 💱 DEX Swap"
                elif _swap_data and isinstance(_swap_data, dict):
                    _dex_label = " + ❌ DEX Failed"

                st.session_state["tx_log"].append({
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    "action": dec["action"],
                    "asset": dec["asset"],
                    "amount": f"${dec['amount_usd']:,.2f}",
                    "confidence": f"{dec['confidence']:.0%}",
                    "risk": f"{dec['risk_score']}/10",
                    "pnl": f"${pnl:+.2f}",
                    "status": ("✅ On-Chain" if exec_result["success"] else "⚠️ Local") + _dex_label,
                    "tx_hash": tx[:20] + "…",
                    "etherscan": f"https://sepolia.etherscan.io/tx/{tx}",
                })

            status_label = "on-chain" if exec_result["success"] else "locally"
            dex_msg = ""
            _sw = exec_result.get("swap")
            if _sw and isinstance(_sw, dict) and _sw.get("success"):
                dex_msg = f" · 💱 DEX Swap: {_sw.get('amount_in', 0):.6f} {_sw.get('token_in', '')} → {_sw.get('amount_out', 0):.6f} {_sw.get('token_out', '')}"
            st.success(f"Trade executed {status_label}! TX: `{tx[:28]}…` · PnL: **${pnl:+.2f}**{dex_msg}")

            _ptimings = exec_result.get("pipeline_timings")
            if _ptimings:
                st.session_state["last_pipeline_timings"] = _ptimings
                _labels = list(reversed(_ptimings.keys()))
                _values = list(reversed(_ptimings.values()))
                _colors = ["#64ffda" if v < 50 else "#ffd740" if v < 200 else "#ff6b6b" for v in _values]
                _wf_fig = go.Figure(go.Bar(
                    y=_labels, x=_values, orientation="h",
                    marker_color=_colors,
                    text=[f"{v:.0f} ms" for v in _values],
                    textposition="auto",
                    textfont=dict(color="#e0e6ed", size=11),
                ))
                _wf_fig.update_layout(
                    title=dict(text="⏱️ Pipeline Execution Waterfall", font=dict(color="#e0e6ed", size=14)),
                    xaxis_title="Latency (ms)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8892a4"),
                    height=220, margin=dict(l=0, r=20, t=40, b=30),
                    xaxis=dict(gridcolor="rgba(100,255,218,0.08)"),
                )
                st.plotly_chart(_wf_fig, use_container_width=True)

            if pnl > 0:
                st.balloons()
            st.rerun()

    elif dec and dec["action"] == "HOLD":
        st.markdown(
            '<div class="dec-box dec-hold" style="text-align:center">'
            '🟡 Recommendation: <b>HOLD</b> — No trade to execute</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#495670">'
            'Run AI Analysis to generate a trade intent.</div>',
            unsafe_allow_html=True,
        )
