"""
Protocol Zero — Main Loop
===========================
Orchestrates the full agent lifecycle:

  ┌──────────┐     ┌─────────┐     ┌──────────────┐     ┌───────────┐
  │ Fetch    │ ──► │  Brain  │ ──► │ Risk Gate    │ ──► │ Execute   │
  │ Market   │     │ (Nova)  │     │ (Limits +    │     │ (Sign +   │
  │ Data     │     │         │     │  Confidence) │     │  Submit)  │
  └──────────┘     └─────────┘     └──────────────┘     └───────────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │ Reputation   │
                                   │ (Log PnL)    │
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

# ── Logging setup ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-5s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("protocol_zero.main")


# ════════════════════════════════════════════════════════════
#  Risk Gate — local pre-flight checks BEFORE on-chain submit
# ════════════════════════════════════════════════════════════

class RiskGate:
    """
    Simple risk manager that tracks intra-session PnL and
    enforces hard limits before any trade is signed.
    """

    def __init__(
        self,
        max_trade_usd: float = config.MAX_TRADE_USD,
        max_daily_loss_usd: float = config.MAX_DAILY_LOSS_USD,
        min_confidence: float = 0.40,
    ) -> None:
        self.max_trade_usd = max_trade_usd
        self.max_daily_loss_usd = max_daily_loss_usd
        self.min_confidence = min_confidence
        self.session_pnl_usd: float = 0.0
        self.trade_log: list[dict] = []

    def check(self, decision: dict) -> tuple[bool, str]:
        """
        Validate a decision against risk limits.

        Returns
        -------
        (passed: bool, reason: str)
        """
        action = decision["action"]

        # HOLD always passes (no capital at risk)
        if action == "HOLD":
            return True, "HOLD — no action required."

        # ── Confidence floor ───────────────────────────────
        if decision["confidence"] < self.min_confidence:
            return False, (
                f"Confidence {decision['confidence']:.0%} < "
                f"minimum {self.min_confidence:.0%}."
            )

        # ── Single-trade cap ──────────────────────────────
        if decision["amount_usd"] > self.max_trade_usd:
            return False, (
                f"Amount ${decision['amount_usd']:.2f} exceeds "
                f"max trade ${self.max_trade_usd:.2f}."
            )

        # ── Daily loss cap ────────────────────────────────
        if self.session_pnl_usd <= -self.max_daily_loss_usd:
            return False, (
                f"Session PnL ${self.session_pnl_usd:.2f} hit "
                f"daily loss limit -${self.max_daily_loss_usd:.2f}."
            )

        return True, "✅ Risk checks passed."

    def record(self, decision: dict, pnl_usd: float = 0.0) -> None:
        """Record a trade execution for session tracking."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": decision["action"],
            "asset": decision["asset"],
            "amount_usd": decision["amount_usd"],
            "pnl_usd": pnl_usd,
        }
        self.trade_log.append(entry)
        self.session_pnl_usd += pnl_usd
        logger.info("📒  Recorded trade — session PnL: $%.2f", self.session_pnl_usd)


# ════════════════════════════════════════════════════════════
#  Single Tick — one full decision cycle
# ════════════════════════════════════════════════════════════

def tick(chain: ChainInteractor, risk: RiskGate) -> dict | None:
    """
    Execute one cycle: fetch → reason → gate → sign → submit.
    Returns the decision dict or None if skipped.
    """
    logger.info("═" * 60)
    logger.info("⏱  New tick at %s", datetime.now(timezone.utc).isoformat())

    # 1 ── Fetch market data ────────────────────────────────
    try:
        df = fetch_market_data()
    except Exception as exc:
        logger.error("Market data fetch failed: %s", exc)
        return None

    # 2 ── Ask the Brain ───────────────────────────────────
    try:
        decision = invoke_brain(df=df)
    except Exception as exc:
        logger.error("Brain invocation failed: %s", exc)
        return None

    logger.info(
        "🧠  Decision: %s %s $%.2f (conf %.0f%%) — %s",
        decision["action"],
        decision["asset"],
        decision["amount_usd"],
        decision["confidence"] * 100,
        decision["reason"],
    )

    # 3 ── Risk Gate ───────────────────────────────────────
    passed, gate_msg = risk.check(decision)
    logger.info("🛡  Risk gate: %s", gate_msg)

    if not passed:
        logger.warning("⛔  Trade BLOCKED by risk gate.")
        return decision

    # 4 ── HOLD shortcut (nothing to sign) ─────────────────
    if decision["action"] == "HOLD":
        logger.info("⏸  HOLD — no on-chain action.")
        risk.record(decision)
        return decision

    # 5 ── Sign & submit intent on-chain ───────────────────
    try:
        tx_hash = chain.submit_intent(decision)
        logger.info("🔗  Intent submitted — TX: %s", tx_hash)
    except Exception as exc:
        logger.error("On-chain submission failed: %s", exc)
        return decision

    # 6 ── Log to Reputation Registry ──────────────────────
    try:
        # PnL is unknown at submit time; log 0 bps — update later
        chain.log_trade_result(
            action_type=decision["action"],
            pnl_bps=0,
            metadata=json.dumps(decision, default=str),
        )
    except Exception as exc:
        logger.warning("Reputation log failed (non-fatal): %s", exc)

    risk.record(decision)
    return decision


# ════════════════════════════════════════════════════════════
#  Entry Point
# ════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Protocol Zero — Agentic DeFi Trading Bot")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--register", action="store_true", help="Register agent on Identity Registry")
    parser.add_argument("--handle", default="ProtocolZero", help="Agent handle for NFT")
    args = parser.parse_args()

    # ── Connect to chain ──────────────────────────────────
    try:
        chain = ChainInteractor()
    except Exception as exc:
        logger.critical("Chain connection failed: %s", exc)
        sys.exit(1)

    # ── One-time registration ─────────────────────────────
    if args.register:
        try:
            chain.register_agent(handle=args.handle)
        except Exception as exc:
            logger.error("Registration failed: %s", exc)
            sys.exit(1)
        logger.info("🎉  Agent registered successfully.")
        return

    # ── Risk gate ─────────────────────────────────────────
    risk = RiskGate()

    # ── Main loop ─────────────────────────────────────────
    if args.loop:
        logger.info("🔄  Entering continuous loop (interval %ds)…", config.LOOP_INTERVAL_SECONDS)
        while True:
            try:
                tick(chain, risk)
            except KeyboardInterrupt:
                logger.info("🛑  Interrupted — shutting down.")
                break
            except Exception as exc:
                logger.error("Tick failed: %s", exc)
            time.sleep(config.LOOP_INTERVAL_SECONDS)
    else:
        # Single shot
        tick(chain, risk)

    # ── Session summary ───────────────────────────────────
    logger.info("═" * 60)
    logger.info("📊  Session summary: %d trades, PnL $%.2f", len(risk.trade_log), risk.session_pnl_usd)
    for t in risk.trade_log:
        logger.info("    %s %s $%.2f — PnL $%.2f", t["action"], t["asset"], t["amount_usd"], t["pnl_usd"])


if __name__ == "__main__":
    main()
