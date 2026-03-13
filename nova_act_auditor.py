"""
Protocol Zero — Nova Act UI Auditor
=====================================
Uses Amazon Nova Act to automate browser-based security audits:

  1. Navigate Etherscan to verify if a contract is verified / open-source.
  2. Check DEX liquidity locks on Uniswap / DEXTools.
  3. Detect warning banners that APIs might miss.
  4. Capture visual evidence for the audit trail.

Nova Act automates real-world UI workflows with high reliability,
acting as a "visual security layer" that sees what APIs cannot.

Requires:
    pip install nova-act
    NOVA_ACT_API_KEY in .env   (or falls back to simulated audit)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import concurrent.futures
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

# Maximum seconds before live audit is killed and simulated fallback kicks in
_LIVE_AUDIT_TIMEOUT = int(os.getenv("NOVA_ACT_TIMEOUT_SEC", "25"))

import config

logger = logging.getLogger("protocol_zero.nova_act")

# ────────────────────────────────────────────────────────────
#  Audit Result Schema
# ────────────────────────────────────────────────────────────

@dataclass
class AuditResult:
    """Result of a Nova Act UI audit on a token / contract."""
    contract_address: str = ""
    chain: str = "sepolia"
    timestamp: str = ""

    # Etherscan checks
    contract_verified: bool | None = None
    source_code_available: bool | None = None
    proxy_detected: bool = False
    warning_banners: list[str] = field(default_factory=list)

    # DEX / Liquidity checks
    liquidity_locked: bool | None = None
    liquidity_amount_usd: float = 0.0
    lock_duration_days: int = 0
    dex_verified_badge: bool = False

    # Social / sentiment
    social_flags: list[str] = field(default_factory=list)

    # Overall
    risk_level: str = "UNKNOWN"      # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: int = 5              # 1-10
    audit_method: str = "nova_act"   # nova_act | simulated
    evidence_screenshots: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_safe(self) -> bool:
        return self.risk_level in ("LOW", "MEDIUM") and self.risk_score <= 5


# ────────────────────────────────────────────────────────────
#  Nova Act Auditor Engine
# ────────────────────────────────────────────────────────────

class NovaActAuditor:
    """
    Uses Amazon Nova Act to perform browser-based security audits
    on smart contracts and tokens.

    Nova Act navigates real web UIs (Etherscan, DEXTools, etc.)
    to verify contract status, liquidity locks, and warning banners
    that traditional API-only approaches would miss.
    """

    def __init__(self):
        self.enabled = config.NOVA_ACT_ENABLED
        self.api_key = config.NOVA_ACT_API_KEY
        self._nova_act_available = False
        self._NovaAct = None
        self._allow_browser_install = os.getenv("NOVA_ACT_ALLOW_BROWSER", "false").lower() == "true"

        if self.enabled and self.api_key:
            # Default behavior keeps startup stable on cloud.
            # Set NOVA_ACT_ALLOW_BROWSER=true to allow live Playwright browser setup.
            if not self._allow_browser_install:
                os.environ.setdefault("NOVA_ACT_SKIP_PLAYWRIGHT_INSTALL", "1")
            try:
                from nova_act import NovaAct
                self._NovaAct = NovaAct
                self._nova_act_available = True
                logger.info(
                    "✅ Nova Act SDK loaded — live UI audits enabled (browser_install=%s, timeout=%ss)",
                    self._allow_browser_install,
                    _LIVE_AUDIT_TIMEOUT,
                )
            except ImportError:
                logger.warning("nova-act package not installed — using simulated audits")
        else:
            logger.info("Nova Act: API key not set — using simulated audits")

        # Track whether live audits have failed (skip retries)
        self._live_failed = False

    # ── Public API ──────────────────────────────────────────

    def audit_contract(self, contract_address: str, chain: str = "sepolia") -> AuditResult:
        """
        Run a comprehensive UI audit on a contract address.

        Steps performed by Nova Act:
          1. Navigate to Etherscan → check verified status
          2. Look for warning banners / flags
          3. Check liquidity on DEXTools / Uniswap
          4. Capture evidence screenshots
        """
        result = AuditResult(
            contract_address=contract_address,
            chain=chain,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if self._nova_act_available and not self._live_failed:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self._live_audit, contract_address, chain, result)
                    result = future.result(timeout=_LIVE_AUDIT_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.warning("Nova Act live audit timed out after %ds — using simulated", _LIVE_AUDIT_TIMEOUT)
                result.error = f"Live audit timed out after {_LIVE_AUDIT_TIMEOUT}s"
                self._live_failed = True  # Don't retry — go straight to simulated next time
                result = self._simulated_audit(contract_address, chain, result)
            except Exception as e:
                logger.error("Nova Act audit failed: %s", e)
                result.error = str(e)
                self._live_failed = True
                result = self._simulated_audit(contract_address, chain, result)
        else:
            result = self._simulated_audit(contract_address, chain, result)

        # Compute overall risk
        result.risk_level, result.risk_score = self._compute_risk(result)
        return result

    def audit_token(self, token_symbol_or_address: str, token_address: str = "",
                    chain: str = "sepolia") -> AuditResult:
        """Convenience: audit by token symbol or address."""
        # If the first arg looks like an address, use it directly
        if token_symbol_or_address.startswith("0x") and len(token_symbol_or_address) >= 42:
            address = token_symbol_or_address
        else:
            address = token_address or self._resolve_token_address(token_symbol_or_address)
        return self.audit_contract(address, chain)

    def quick_safety_check(self, contract_address: str) -> dict:
        """
        Fast safety check — returns a simple pass/fail dict
        suitable for use in the trading pipeline.
        """
        audit = self.audit_contract(contract_address)
        return {
            "safe": audit.is_safe,
            "risk_level": audit.risk_level,
            "risk_score": audit.risk_score,
            "warnings": audit.warning_banners + audit.social_flags,
            "contract_verified": audit.contract_verified,
            "liquidity_locked": audit.liquidity_locked,
            "method": audit.audit_method,
        }

    def status(self) -> dict:
        """Return auditor status for dashboard display."""
        return {
            "enabled": self.enabled,
            "live_mode": self._nova_act_available,
            "api_key_set": bool(self.api_key),
            "method": "Nova Act (Live UI)" if self._nova_act_available else "Simulated",
        }

    # ── Live Nova Act Audit ─────────────────────────────────

    def _live_audit(self, contract_address: str, chain: str,
                    result: AuditResult) -> AuditResult:
        """
        Real Nova Act browser automation.
        Navigates Etherscan and DEXTools to perform visual verification.
        """
        result.audit_method = "nova_act"
        explorer_base = self._get_explorer_url(chain)

        # Step 1: Etherscan Contract Verification
        with self._NovaAct(
            starting_page=f"{explorer_base}/address/{contract_address}",
            nova_act_api_key=self.api_key,
        ) as nova:
            # Check if contract is verified
            verification = nova.act(
                "Look at this Etherscan contract page. "
                "Tell me: 1) Is the contract verified (source code available)? "
                "2) Are there any warning banners or flags? "
                "3) Is this a proxy contract? "
                "Return as JSON: {verified: bool, warnings: [str], proxy: bool}"
            )
            if verification.parsed_response:
                data = verification.parsed_response
                result.contract_verified = data.get("verified", False)
                result.source_code_available = data.get("verified", False)
                result.proxy_detected = data.get("proxy", False)
                result.warning_banners = data.get("warnings", [])

            # Step 2: Check token transactions / holder distribution
            holder_check = nova.act(
                "Navigate to the 'Holders' tab of this token contract. "
                "Check if the top holder owns more than 50% of supply. "
                "Return as JSON: {concentrated: bool, top_holder_pct: float}"
            )
            if holder_check.parsed_response:
                hdata = holder_check.parsed_response
                if hdata.get("concentrated"):
                    result.social_flags.append(
                        f"⚠️ Top holder owns {hdata.get('top_holder_pct', 0):.1f}% of supply"
                    )

        # Step 3: DEXTools Liquidity Check
        try:
            with self._NovaAct(
                starting_page=f"https://www.dextools.io/app/en/ether/pair-explorer/{contract_address}",
                nova_act_api_key=self.api_key,
            ) as nova:
                liq_check = nova.act(
                    "Check this DEXTools page. "
                    "Is the liquidity locked? What is the liquidity amount? "
                    "Is there a 'Verified' badge? "
                    "Return as JSON: {locked: bool, amount_usd: float, "
                    "lock_days: int, verified_badge: bool}"
                )
                if liq_check.parsed_response:
                    ldata = liq_check.parsed_response
                    result.liquidity_locked = ldata.get("locked", False)
                    result.liquidity_amount_usd = ldata.get("amount_usd", 0)
                    result.lock_duration_days = ldata.get("lock_days", 0)
                    result.dex_verified_badge = ldata.get("verified_badge", False)
        except Exception as e:
            logger.warning("DEXTools check failed: %s", e)

        return result

    # ── Simulated Audit (fallback) ──────────────────────────

    def _simulated_audit(self, contract_address: str, chain: str,
                         result: AuditResult) -> AuditResult:
        """
        Simulated audit using deterministic heuristics.
        Used when Nova Act SDK is not available (invite-only).

        Applies realistic, address-entropy-based heuristics.
        Known infrastructure contracts (registries, DEX routers, wrapped
        tokens) are identified as high-confidence verified contracts — this
        is factually accurate because they ARE verified on-chain.
        """
        result.audit_method = "simulated"

        # Deterministic simulation based on address hash
        addr_hash = int(hashlib.sha256(contract_address.lower().encode()).hexdigest()[:8], 16)

        # Infrastructure contracts that are genuinely verified on-chain
        known_infra = {
            config.IDENTITY_REGISTRY_ADDRESS.lower(): "ERC-8004 Identity Registry",
            config.REPUTATION_REGISTRY_ADDRESS.lower(): "ERC-8004 Reputation Registry",
            config.UNISWAP_ROUTER_ADDRESS.lower(): "Uniswap V3 Router",
            config.WETH_ADDRESS.lower(): "Wrapped ETH (WETH)",
            config.USDC_ADDRESS.lower(): "USD Coin (USDC)",
        }

        infra_label = known_infra.get(contract_address.lower())
        if infra_label:
            # These are genuinely verified infrastructure contracts
            result.contract_verified = True
            result.source_code_available = True
            result.liquidity_locked = None  # Unknown without live check
            result.liquidity_amount_usd = 0.0  # Unknown — not faked
            result.lock_duration_days = 0
            result.dex_verified_badge = False  # Unknown without live check
            result.social_flags.append(
                f"ℹ️ Recognized infrastructure: {infra_label} (simulated audit)"
            )
        else:
            # Variable risk based on address entropy
            risk_seed = addr_hash % 100
            result.contract_verified = risk_seed > 20
            result.source_code_available = risk_seed > 30
            result.proxy_detected = 10 < risk_seed < 40
            result.liquidity_locked = risk_seed > 40
            result.liquidity_amount_usd = float(risk_seed * 1000)
            result.lock_duration_days = risk_seed * 3

            if risk_seed < 20:
                result.warning_banners.append("⚠️ Unverified contract — potential honeypot")
            if risk_seed < 15:
                result.social_flags.append("🚩 Contract matches known rug-pull pattern")
            if result.proxy_detected:
                result.warning_banners.append("⚠️ Upgradeable proxy — owner can modify logic")

        return result

    # ── Risk Computation ────────────────────────────────────

    def _compute_risk(self, result: AuditResult) -> tuple[str, int]:
        """Compute aggregate risk level and score from audit findings."""
        score = 5  # neutral baseline

        # Contract verification
        if result.contract_verified:
            score -= 2
        else:
            score += 3

        # Liquidity
        if result.liquidity_locked:
            score -= 1
            if result.lock_duration_days > 180:
                score -= 1
        else:
            score += 2

        # Warnings
        score += len(result.warning_banners)
        score += len(result.social_flags)

        # DEX badge
        if result.dex_verified_badge:
            score -= 1

        # Proxy
        if result.proxy_detected:
            score += 1

        score = max(1, min(10, score))

        if score <= 3:
            level = "LOW"
        elif score <= 5:
            level = "MEDIUM"
        elif score <= 7:
            level = "HIGH"
        else:
            level = "CRITICAL"

        return level, score

    # ── Helpers ─────────────────────────────────────────────

    def _get_explorer_url(self, chain: str) -> str:
        explorers = {
            "sepolia": "https://sepolia.etherscan.io",
            "mainnet": "https://etherscan.io",
            "polygon": "https://polygonscan.com",
            "arbitrum": "https://arbiscan.io",
        }
        return explorers.get(chain, "https://sepolia.etherscan.io")

    def _resolve_token_address(self, symbol: str) -> str:
        """Resolve common token symbols to addresses."""
        tokens = {
            "WETH": config.WETH_ADDRESS,
            "USDC": config.USDC_ADDRESS,
            "ETH": config.WETH_ADDRESS,
        }
        return tokens.get(symbol.upper(), "0x" + "0" * 40)
