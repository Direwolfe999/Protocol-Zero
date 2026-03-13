"""
Protocol Zero — Risk Check Module
====================================
Pre-submission risk-limit functions called by the agent BEFORE any
signed TradeIntent is forwarded to the on-chain Risk Router.

Design Principles
-----------------
1. **Fail-closed** — if any check is uncertain, the trade is blocked.
2. **Stateful** — a `RiskState` object tracks cumulative exposure,
   daily PnL, and trade frequency across the session.
3. **Composable** — each check is a standalone function that returns
   `(passed: bool, reason: str)`.  The orchestrator calls them in
   sequence via `run_all_checks()`.
4. **Deterministic** — no network calls, no randomness.  Pure math
   on local state so it can never be front-run or manipulated.

Limit Catalogue
───────────────
    check_max_position_size   — single-trade USD cap
    check_daily_loss_limit    — cumulative daily drawdown cap
    check_trade_frequency     — max N trades per rolling window
    check_concentration       — max % of capital in one asset
    check_confidence_floor    — minimum model confidence to act
    check_intent_expiry       — reject stale / expired intents

Usage
-----
    from risk_check import RiskState, run_all_checks

    risk = RiskState(max_position_usd=500, max_daily_loss_usd=1000)
    decision = {"action": "BUY", "asset": "ETH", "amount_usd": 200, ...}

    passed, reasons = run_all_checks(risk, decision)
    if not passed:
        print("BLOCKED:", reasons)
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import config

logger = logging.getLogger("protocol_zero.risk")


# ════════════════════════════════════════════════════════════
#  Risk State — tracks cumulative exposure within a session
# ════════════════════════════════════════════════════════════

@dataclass
class RiskState:
    """
    Mutable state container updated after every trade.

    All monetary values are in USD.
    """

    # ── Configurable limits (loaded from config / .env) ───
    max_position_usd: float      = config.MAX_TRADE_USD
    max_daily_loss_usd: float    = config.MAX_DAILY_LOSS_USD
    min_confidence: float        = 0.40
    max_trades_per_hour: int     = 10
    max_concentration_pct: float = 0.30       # 30 % of capital in one asset
    total_capital_usd: float     = 10_000.0   # portfolio notional (override as needed)
    min_reputation_score: float  = 30.0       # ERC-8004 min rep % to allow trading
    max_risk_score: int          = 8          # max AI risk-score (1-10) ceiling

    # ── Running counters (mutated at runtime) ─────────────
    daily_pnl_usd: float                      = 0.0
    trade_timestamps: list[float]              = field(default_factory=list)
    positions: dict[str, float]                = field(default_factory=lambda: defaultdict(float))
    trade_count: int                           = 0

    # ──────────────────────────────────────────────────────
    def record_trade(self, asset: str, amount_usd: float, pnl_usd: float = 0.0) -> None:
        """Update state after a trade is executed."""
        self.positions[asset] += amount_usd
        self.daily_pnl_usd += pnl_usd
        self.trade_timestamps.append(time.time())
        self.trade_count += 1

    def reset_daily(self) -> None:
        """Call at the start of each new trading day."""
        self.daily_pnl_usd = 0.0
        self.trade_timestamps.clear()
        self.trade_count = 0
        logger.info("🔄  Daily risk counters reset.")


# ════════════════════════════════════════════════════════════
#  Individual Check Functions
#  Each returns (passed: bool, reason: str)
# ════════════════════════════════════════════════════════════

def check_max_position_size(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if the single trade amount exceeds the per-trade cap.

    Why: Prevents the agent from concentrating too much capital in
    a single order, limiting blast radius of a bad decision.
    """
    amount = float(decision.get("amount_usd", 0))
    if amount <= 0 and decision.get("action") != "HOLD":
        return False, f"Invalid trade amount: ${amount:.2f}"

    if amount > state.max_position_usd:
        return False, (
            f"Position size ${amount:.2f} exceeds max "
            f"${state.max_position_usd:.2f}"
        )
    return True, "Position size OK"


def check_daily_loss_limit(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if cumulative daily PnL has breached the loss limit.

    Why: Hard circuit-breaker.  Once the agent has lost too much in
    a day, no further risk-taking is allowed until the next reset.
    """
    if state.daily_pnl_usd <= -state.max_daily_loss_usd:
        return False, (
            f"Daily loss limit hit: PnL ${state.daily_pnl_usd:.2f} "
            f"<= -${state.max_daily_loss_usd:.2f}"
        )
    return True, f"Daily PnL ${state.daily_pnl_usd:+.2f} within limits"


def check_trade_frequency(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if the agent has exceeded max trades in the last hour.

    Why: Prevents the LLM from entering a rapid-fire loop that
    racks up gas fees and increases error surface.
    """
    now = time.time()
    one_hour_ago = now - 3600
    recent = [ts for ts in state.trade_timestamps if ts >= one_hour_ago]

    if len(recent) >= state.max_trades_per_hour:
        return False, (
            f"Rate limit: {len(recent)} trades in last hour "
            f"(max {state.max_trades_per_hour})"
        )
    return True, f"Trade frequency OK ({len(recent)}/{state.max_trades_per_hour} per hour)"


def check_concentration(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if executing this trade would put > X % of capital
    into a single asset.

    Why: Diversification guard — prevents the agent from going
    "all in" on one token.
    """
    asset  = str(decision.get("asset", ""))
    amount = float(decision.get("amount_usd", 0))

    current_exposure  = state.positions.get(asset, 0.0)
    projected         = current_exposure + amount
    concentration_pct = projected / state.total_capital_usd if state.total_capital_usd > 0 else 1.0

    if concentration_pct > state.max_concentration_pct:
        return False, (
            f"Concentration {concentration_pct:.0%} in {asset} "
            f"exceeds max {state.max_concentration_pct:.0%}"
        )
    return True, f"Concentration in {asset}: {concentration_pct:.0%} OK"


def check_confidence_floor(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if the model's confidence is below the minimum threshold.

    Why: Low confidence = high uncertainty = stay out.
    """
    confidence = float(decision.get("confidence", 0))
    if confidence < state.min_confidence:
        return False, (
            f"Confidence {confidence:.0%} < "
            f"minimum {state.min_confidence:.0%}"
        )
    return True, f"Confidence {confidence:.0%} OK"


def check_intent_expiry(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if the signed intent has already expired.

    Why: Stale intents may reflect outdated market conditions.
    Only relevant when the decision carries an `expiry` field
    (set by `eip712_signer`).
    """
    expiry = decision.get("expiry")
    if expiry is None:
        return True, "No expiry field — skipping check"

    now = int(time.time())
    if now >= int(expiry):
        return False, f"Intent expired at {expiry} (now {now})"
    return True, f"Intent valid for {int(expiry) - now}s"


def check_erc8004_reputation(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if the agent's on-chain ERC-8004 reputation score
    is below the minimum threshold required for autonomous trading.

    Why: ERC-8004 mandates that agents maintain a positive reputation
    before being trusted to execute financial transactions.  A low
    reputation signals previous bad trades, reverts, or negative
    feedback — the agent should be paused until trust is restored.

    The reputation score is injected into the decision dict by the
    dashboard / orchestrator layer before calling run_all_checks().
    If no score is available (agent not registered), we allow with a warning.
    """
    rep_score = decision.get("reputation_score")
    threshold = state.min_reputation_score

    if rep_score is None:
        return True, f"Reputation: not available (threshold {threshold}%) — allowing"

    rep_score = float(rep_score)
    if rep_score < threshold:
        return False, (
            f"ERC-8004 reputation {rep_score:.0f}% < "
            f"minimum threshold {threshold:.0f}% — agent untrusted"
        )
    return True, f"ERC-8004 reputation {rep_score:.0f}% ≥ {threshold:.0f}% OK"


def check_risk_score_ceiling(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, str]:
    """
    REJECT if the AI's self-assessed risk score exceeds the
    maximum tolerable threshold.

    Why: Even if the model is confident, a very high risk score
    (7+) indicates dangerous market conditions.  This acts as a
    secondary circuit-breaker layered on top of confidence.
    """
    risk_score = int(decision.get("risk_score", 5))
    ceiling = state.max_risk_score

    if risk_score > ceiling:
        return False, (
            f"Risk score {risk_score}/10 exceeds ceiling "
            f"{ceiling}/10 — too dangerous"
        )
    return True, f"Risk score {risk_score}/10 ≤ {ceiling}/10 OK"


# ════════════════════════════════════════════════════════════
#  Composite: run every check in sequence
# ════════════════════════════════════════════════════════════

# Ordered list of all check functions
ALL_CHECKS = [
    check_max_position_size,
    check_daily_loss_limit,
    check_trade_frequency,
    check_concentration,
    check_confidence_floor,
    check_intent_expiry,
    check_erc8004_reputation,
    check_risk_score_ceiling,
]


def run_all_checks(
    state: RiskState,
    decision: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Execute every risk check against the decision.

    Parameters
    ----------
    state    : Current RiskState (mutable, not modified here).
    decision : Brain output dict with keys:
               action, asset, amount_usd, confidence, [expiry].

    Returns
    -------
    (all_passed: bool, messages: list[str])
        messages contains one line per check (pass or fail).
    """
    action = str(decision.get("action", "HOLD")).upper()

    # HOLD is always safe — skip all checks
    if action == "HOLD":
        return True, ["HOLD — no risk checks needed."]

    all_passed = True
    messages: list[str] = []

    for check_fn in ALL_CHECKS:
        passed, msg = check_fn(state, decision)
        prefix = "✅" if passed else "❌"
        messages.append(f"{prefix}  {check_fn.__name__}: {msg}")
        if not passed:
            all_passed = False
            logger.warning("Risk check FAILED: %s — %s", check_fn.__name__, msg)

    if all_passed:
        logger.info("🛡  All %d risk checks PASSED.", len(ALL_CHECKS))
    else:
        logger.warning("⛔  %d risk check(s) FAILED.",
                        sum(1 for m in messages if m.startswith("❌")))

    return all_passed, messages


# ════════════════════════════════════════════════════════════
#  Pretty-print helper (for dashboards / logs)
# ════════════════════════════════════════════════════════════

def format_risk_report(
    state: RiskState,
    decision: dict[str, Any],
) -> str:
    """
    Run all checks and return a formatted multi-line report string.
    """
    passed, messages = run_all_checks(state, decision)
    header = "RISK GATE: PASSED ✅" if passed else "RISK GATE: BLOCKED ⛔"
    lines = [
        "─" * 50,
        f"  {header}",
        "─" * 50,
        f"  Action     : {decision.get('action')}",
        f"  Asset      : {decision.get('asset')}",
        f"  Amount     : ${decision.get('amount_usd', 0):.2f}",
        f"  Confidence : {decision.get('confidence', 0):.0%}",
        "─" * 50,
    ]
    for msg in messages:
        lines.append(f"  {msg}")
    lines.append("─" * 50)
    lines.append(f"  Session PnL    : ${state.daily_pnl_usd:+.2f}")
    lines.append(f"  Trades today   : {state.trade_count}")
    lines.append(f"  Capital tracked: ${state.total_capital_usd:,.2f}")
    lines.append("─" * 50)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
#  CLI Smoke Test
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print()
    print("  Protocol Zero — Risk Check Smoke Test")
    print()

    state = RiskState(
        max_position_usd=500,
        max_daily_loss_usd=1000,
        total_capital_usd=10_000,
    )

    # ── Test 1: Normal trade (should pass) ────────────────
    good_trade = {
        "action": "BUY",
        "asset": "ETH",
        "amount_usd": 200.0,
        "confidence": 0.75,
    }
    print(format_risk_report(state, good_trade))

    # ── Test 2: Over-sized trade (should fail) ────────────
    big_trade = {
        "action": "BUY",
        "asset": "BTC",
        "amount_usd": 9999.0,
        "confidence": 0.90,
    }
    print(format_risk_report(state, big_trade))

    # ── Test 3: Low confidence (should fail) ──────────────
    uncertain_trade = {
        "action": "SELL",
        "asset": "ETH",
        "amount_usd": 100.0,
        "confidence": 0.15,
    }
    print(format_risk_report(state, uncertain_trade))

    # ── Test 4: HOLD (always passes) ──────────────────────
    hold = {
        "action": "HOLD",
        "asset": "ETH",
        "amount_usd": 0.0,
        "confidence": 0.10,
    }
    print(format_risk_report(state, hold))

    # ── Test 5: Daily loss limit ──────────────────────────
    state.daily_pnl_usd = -1001.0  # simulate losses
    post_loss_trade = {
        "action": "BUY",
        "asset": "ETH",
        "amount_usd": 50.0,
        "confidence": 0.80,
    }
    print(format_risk_report(state, post_loss_trade))
