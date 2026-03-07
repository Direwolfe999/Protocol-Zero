"""
Protocol Zero — Main Loop (ERC-8004 Compliant Pipeline)
=========================================================
Orchestrates the full agent lifecycle with real-time integration:

  ┌──────────┐     ┌─────────┐     ┌──────────────┐     ┌───────────────┐
  │ Fetch    │ ──► │  Brain  │ ──► │ Risk Check   │ ──► │ Validate +    │
  │ Market   │     │ (Nova)  │     │ (6 checks)   │     │ Sign (EIP712) │
  │ Data     │     │         │     │              │     │               │
  └──────────┘     └─────────┘     └──────────────┘     └───────┬───────┘
                                                                │
                          ┌─────────────────────────────────────┤
                          ▼                                     ▼
                   ┌──────────────┐                 ┌───────────────────┐
                   │ Validation   │                 │ Reputation        │
                   │ Artifacts    │                 │ (giveFeedback)    │
                   │ (keccak256)  │                 │                   │
                   └──────────────┘                 └───────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Performance  │
                   │ Tracker      │
                   │ (Sharpe etc) │
                   └──────────────┘

Usage:
    python main.py              # one-shot
    python main.py --loop       # continuous loop
    python main.py --register   # register agent on Identity Registry
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone

import config
from brain import fetch_market_data, invoke_brain
from chain_interactor import ChainInteractor
from exceptions import MarketDataError, BrainError, ChainError, ProtocolZeroError
from risk_check import RiskState, run_all_checks, format_risk_report
from sign_trade import validate_and_sign
from performance_tracker import PerformanceTracker
from validation_artifacts import ValidationArtifactBuilder
from dex_executor import DexExecutor

# ── Logging setup ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-5s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("protocol_zero.main")


# ════════════════════════════════════════════════════════════
#  Single Tick — one full decision cycle
# ════════════════════════════════════════════════════════════

def tick(
    chain: ChainInteractor,
    risk_state: RiskState,
    performance: PerformanceTracker,
    artifact_builder: ValidationArtifactBuilder,
    dex: DexExecutor | None = None,
) -> dict | None:
    """
    Execute one full cycle:
      fetch → brain → risk_check → sign_trade → chain → validation_artifact → reputation → performance

    Returns the decision dict or None if skipped.
    """
    logger.info("═" * 60)
    logger.info("⏱  New tick at %s", datetime.now(timezone.utc).isoformat())

    # 1 ── Fetch market data ────────────────────────────────
    try:
        df = fetch_market_data()
    except MarketDataError as exc:
        logger.error("Market data fetch failed: %s (details: %s)", exc, exc.details)
        return None
    except Exception as exc:
        logger.error("Unexpected error fetching market data: %s", exc)
        return None

    # 2 ── Ask the Brain ───────────────────────────────────
    try:
        decision = invoke_brain(df=df)
    except BrainError as exc:
        logger.error("Brain invocation failed: %s (details: %s)", exc, exc.details)
        return None
    except Exception as exc:
        logger.error("Unexpected brain error: %s", exc)
        return None

    logger.info(
        "🧠  Decision: %s %s $%.2f (conf %.0f%% risk %d regime %s) — %s",
        decision["action"],
        decision["asset"],
        decision["amount_usd"],
        decision["confidence"] * 100,
        decision["risk_score"],
        decision["market_regime"],
        decision["reason"],
    )

    # 3 ── Risk Check (6 checks) ──────────────────────────
    risk_passed, risk_messages = run_all_checks(risk_state, decision)
    logger.info("🛡  Risk gate: %s", "PASSED ✅" if risk_passed else "BLOCKED ⛔")
    for msg in risk_messages:
        logger.info("    %s", msg)

    if not risk_passed:
        logger.warning("⛔  Trade BLOCKED by risk checks.")
        # Still build validation artifact for audit trail
        artifact_builder.build_artifact(
            decision=decision,
            market_data=df,
            risk_results=(risk_passed, risk_messages),
        )
        return decision

    # 4 ── HOLD shortcut (nothing to sign) ─────────────────
    if decision["action"] == "HOLD":
        logger.info("⏸  HOLD — no on-chain action.")
        risk_state.record_trade(decision.get("asset", ""), 0, 0)
        artifact_builder.build_artifact(
            decision=decision,
            market_data=df,
            risk_results=(risk_passed, risk_messages),
        )
        return decision

    # 5 ── Validate & Sign (EIP-712) ──────────────────────
    try:
        sign_result = validate_and_sign(decision, broadcast=False)
        if sign_result["status"] == "rejected":
            logger.warning("⛔  Trade REJECTED by sign_trade validation:")
            for err in sign_result["validation"]["errors"]:
                logger.warning("    • %s", err)
            return decision
        logger.info("🔏  Trade signed successfully — signer: %s",
                    sign_result.get("signed", {}).get("signer", "?"))
    except Exception as exc:
        logger.error("Sign/validate failed: %s", exc)
        sign_result = None

    # 6 ── Submit intent on-chain via Validation Registry ──
    tx_hash = ""
    try:
        tx_hash = chain.submit_intent(decision)
        logger.info("🔗  Intent submitted — TX: %s", tx_hash)
    except Exception as exc:
        logger.error("On-chain submission failed: %s", exc)

    # 6b ── Execute DEX swap (Uniswap V3) ─────────────────
    swap_result = None
    if dex and dex.enabled:
        try:
            current_price = float(df["close"].iloc[-1]) if df is not None and len(df) > 0 else 0.0
            swap_result = dex.execute_swap(decision, current_price)
            if swap_result.success:
                logger.info(
                    "💱  DEX swap executed — TX: %s | In: %.6f %s → Out: %.6f %s | Gas: %.6f ETH",
                    swap_result.tx_hash,
                    swap_result.amount_in, swap_result.token_in,
                    swap_result.amount_out, swap_result.token_out,
                    swap_result.gas_cost_eth,
                )
            else:
                logger.warning("⚠️  DEX swap failed: %s", swap_result.error)
        except Exception as exc:
            logger.error("DEX execution failed: %s", exc)
    elif dex and not dex.enabled:
        logger.info("💤  DEX execution disabled (set DEX_ENABLED=true to activate)")

    # 7 ── Build validation artifact ──────────────────────
    perf_report = performance.get_report()
    artifact = artifact_builder.build_artifact(
        decision=decision,
        market_data=df,
        risk_results=(risk_passed, risk_messages),
        signed_intent=sign_result,
        performance_report=perf_report,
    )
    logger.info("📋  Validation artifact: %s", artifact.artifact_id)

    # 8 ── Log to Reputation Registry ──────────────────────
    try:
        chain.log_trade_result(
            action_type=decision["action"],
            pnl_bps=0,  # PnL unknown at submission — update later
            metadata=json.dumps(decision, default=str),
        )
    except Exception as exc:
        logger.warning("Reputation log failed (non-fatal): %s", exc)

    # 9 ── Record in performance tracker ──────────────────
    performance.record_trade(
        action=decision["action"],
        asset=decision["asset"],
        amount_usd=decision["amount_usd"],
        pnl_usd=0.0,  # actual PnL resolved later
        confidence=decision["confidence"],
        risk_score=decision["risk_score"],
        market_regime=decision["market_regime"],
    )

    # 10 ── Update risk state ─────────────────────────────
    risk_state.record_trade(
        decision["asset"],
        decision["amount_usd"],
    )

    return decision


# ════════════════════════════════════════════════════════════
#  Entry Point
# ════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Protocol Zero — ERC-8004 Agentic DeFi Trading Bot")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--register", action="store_true", help="Register agent on Identity Registry")
    parser.add_argument("--agent-uri", default="", help="Agent URI for ERC-8004 registration")
    args = parser.parse_args()

    # ── Connect to chain ──────────────────────────────────
    try:
        chain = ChainInteractor()
    except (ChainError, ProtocolZeroError) as exc:
        logger.critical("Chain connection failed: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected chain error: %s", exc)
        sys.exit(1)

    # ── One-time registration ─────────────────────────────
    if args.register:
        try:
            chain.register_agent(agent_uri=args.agent_uri)
        except Exception as exc:
            logger.error("Registration failed: %s", exc)
            sys.exit(1)
        logger.info("🎉  Agent registered successfully on ERC-8004 Identity Registry.")
        return

    # ── Initialize subsystems ─────────────────────────────
    risk_state = RiskState(
        max_position_usd=config.MAX_TRADE_USD,
        max_daily_loss_usd=config.MAX_DAILY_LOSS_USD,
        total_capital_usd=config.TOTAL_CAPITAL_USD,
    )
    performance = PerformanceTracker(initial_capital=config.TOTAL_CAPITAL_USD)
    artifact_builder = ValidationArtifactBuilder(chain_interactor=chain)

    # ── DEX Executor (optional — controlled by DEX_ENABLED) ──
    dex = None
    try:
        dex = DexExecutor()
        if dex.enabled:
            logger.info("💱  DEX Executor LIVE — swaps will execute on Uniswap V3")
            balances = dex.get_balances()
            logger.info("    Wallet: %s | ETH: %.4f | WETH: %.6f | USDC: %.2f",
                        balances["wallet"], balances["eth"],
                        balances["weth"], balances["usdc"])
        else:
            logger.info("💤  DEX Executor loaded but DISABLED (set DEX_ENABLED=true)")
    except Exception as exc:
        logger.warning("⚠️  DEX Executor unavailable: %s", exc)
        dex = None

    # ── Main loop ─────────────────────────────────────────
    if args.loop:
        logger.info("🔄  Entering continuous loop (interval %ds)…", config.LOOP_INTERVAL_SECONDS)
        while True:
            try:
                tick(chain, risk_state, performance, artifact_builder, dex=dex)
            except KeyboardInterrupt:
                logger.info("🛑  Interrupted — shutting down.")
                break
            except Exception as exc:
                logger.error("Tick failed: %s", exc)
            time.sleep(config.LOOP_INTERVAL_SECONDS)
    else:
        # Single shot
        tick(chain, risk_state, performance, artifact_builder, dex=dex)

    # ── Session summary ───────────────────────────────────
    logger.info("═" * 60)
    logger.info(performance.format_report())


if __name__ == "__main__":
    main()
