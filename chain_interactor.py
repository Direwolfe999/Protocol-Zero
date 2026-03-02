"""
Protocol Zero — Chain Interactor (Blockchain Bridge)
=====================================================
Responsibilities:
  1. Connect to an EVM chain via Web3.
  2. Register the agent on the ERC-8004 Identity Registry (mint handle NFT).
  3. Log PnL to the Reputation Registry.
  4. Sign trade intents using EIP-712 structured data.
  5. Submit signed intents to the Validation (Risk Router) Registry.

ERC-8004 Standard — Three Registries:
  • Identity Registry   — NFT-based agent handle (one-time mint).
  • Reputation Registry  — Append-only PnL / action log.
  • Validation Registry  — Verifies EIP-712 signed trade intents.

All financial actions are signed by the bot's private key.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config

logger = logging.getLogger("protocol_zero.chain")

# ════════════════════════════════════════════════════════════
#  Minimal ABI Stubs for the Three ERC-8004 Registries
#  Replace with your actual deployed ABI JSONs.
# ════════════════════════════════════════════════════════════

IDENTITY_REGISTRY_ABI: list[dict] = [
    # registerAgent(string handle) → uint256 tokenId
    {
        "inputs": [{"internalType": "string", "name": "handle", "type": "string"}],
        "name": "registerAgent",
        "outputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # isRegistered(address agent) → bool
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    # getTokenId(address agent) → uint256
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getTokenId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

REPUTATION_REGISTRY_ABI: list[dict] = [
    # logAction(address agent, string actionType, int256 pnlBps, string metadata)
    {
        "inputs": [
            {"internalType": "address", "name": "agent", "type": "address"},
            {"internalType": "string", "name": "actionType", "type": "string"},
            {"internalType": "int256", "name": "pnlBps", "type": "int256"},
            {"internalType": "string", "name": "metadata", "type": "string"},
        ],
        "name": "logAction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # getReputation(address agent) → (uint256 totalTrades, int256 cumulativePnlBps)
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getReputation",
        "outputs": [
            {"internalType": "uint256", "name": "totalTrades", "type": "uint256"},
            {"internalType": "int256", "name": "cumulativePnlBps", "type": "int256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

VALIDATION_REGISTRY_ABI: list[dict] = [
    # submitIntent(bytes signature, bytes32 intentHash) → bool valid
    {
        "inputs": [
            {"internalType": "bytes", "name": "signature", "type": "bytes"},
            {"internalType": "bytes32", "name": "intentHash", "type": "bytes32"},
        ],
        "name": "submitIntent",
        "outputs": [{"internalType": "bool", "name": "valid", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


# ════════════════════════════════════════════════════════════
#  ChainInteractor — the single entry-point for on-chain ops
# ════════════════════════════════════════════════════════════

class ChainInteractor:
    """High-level wrapper around Web3 for ERC-8004 compliance."""

    def __init__(self) -> None:
        # ── Web3 connection ────────────────────────────────
        self.w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
        # Support PoA chains (Polygon, BSC, testnets …)
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot reach RPC: {config.RPC_URL}")
        logger.info("🔗  Connected to chain %s (block %s)", config.CHAIN_ID, self.w3.eth.block_number)

        # ── Wallet ────────────────────────────────────────
        self.account: Account = Account.from_key(config.PRIVATE_KEY)
        self.address: str = self.account.address
        logger.info("🤖  Agent wallet: %s", self.address)

        # ── Contract handles ──────────────────────────────
        self.identity = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.IDENTITY_REGISTRY_ADDRESS),
            abi=IDENTITY_REGISTRY_ABI,
        )
        self.reputation = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.REPUTATION_REGISTRY_ADDRESS),
            abi=REPUTATION_REGISTRY_ABI,
        )
        self.validation = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.VALIDATION_REGISTRY_ADDRESS),
            abi=VALIDATION_REGISTRY_ABI,
        )

    # ────────────────────────────────────────────────────────
    #  Internal: build, sign & send a transaction
    # ────────────────────────────────────────────────────────

    def _send_tx(self, fn_call) -> str:
        """
        Build, sign, and broadcast a contract function call.
        Returns the transaction hash hex string.
        """
        nonce = self.w3.eth.get_transaction_count(self.address)
        tx = fn_call.build_transaction({
            "from": self.address,
            "nonce": nonce,
            "gas": 300_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": config.CHAIN_ID,
        })
        signed = self.w3.eth.account.sign_transaction(tx, private_key=config.PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info("📤  TX sent: %s", tx_hash.hex())

        # Wait for receipt (timeout 120 s)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] != 1:
            raise RuntimeError(f"TX reverted: {tx_hash.hex()}")
        logger.info("✅  TX confirmed in block %s", receipt["blockNumber"])
        return tx_hash.hex()

    # ────────────────────────────────────────────────────────
    #  1.  Identity Registry — register / check agent
    # ────────────────────────────────────────────────────────

    def is_registered(self) -> bool:
        """Check if this wallet has already minted an agent handle NFT."""
        try:
            return self.identity.functions.isRegistered(self.address).call()
        except Exception:
            logger.warning("isRegistered call failed — assuming not registered.")
            return False

    def register_agent(self, handle: str = "ProtocolZero") -> str:
        """
        Mint an ERC-8004 Identity NFT with the given handle.
        Idempotent: skips if already registered.
        """
        if self.is_registered():
            logger.info("Agent already registered on Identity Registry.")
            return ""
        logger.info("📝  Registering agent handle '%s' …", handle)
        fn = self.identity.functions.registerAgent(handle)
        return self._send_tx(fn)

    def get_token_id(self) -> int:
        """Return the NFT token ID for this agent."""
        return self.identity.functions.getTokenId(self.address).call()

    # ────────────────────────────────────────────────────────
    #  2.  Reputation Registry — log PnL
    # ────────────────────────────────────────────────────────

    def log_trade_result(
        self,
        action_type: str,
        pnl_bps: int,
        metadata: str = "",
    ) -> str:
        """
        Append a trade result to the on-chain reputation log.

        Parameters
        ----------
        action_type : str   "BUY", "SELL", "HOLD"
        pnl_bps     : int   Profit/loss in basis points (+150 = +1.5 %)
        metadata    : str   Arbitrary JSON blob for context
        """
        logger.info("📊  Logging %s | PnL %+d bps", action_type, pnl_bps)
        fn = self.reputation.functions.logAction(
            self.address,
            action_type,
            pnl_bps,
            metadata,
        )
        return self._send_tx(fn)

    def get_reputation(self) -> dict:
        """Query cumulative reputation for this agent."""
        total, pnl = self.reputation.functions.getReputation(self.address).call()
        return {"total_trades": total, "cumulative_pnl_bps": pnl}

    # ────────────────────────────────────────────────────────
    #  3.  Validation Registry — EIP-712 signed trade intents
    # ────────────────────────────────────────────────────────

    def sign_trade_intent(self, decision: dict) -> tuple[bytes, bytes]:
        """
        Create an EIP-712 typed-data signature for a trade intent.

        Parameters
        ----------
        decision : dict with keys action, asset, amount_usd, reason, confidence

        Returns
        -------
        (signature_bytes, intent_hash_bytes32)
        """
        # ── EIP-712 domain & message ──────────────────────
        domain_data = {
            "name": "ProtocolZero",
            "version": "1",
            "chainId": config.CHAIN_ID,
            "verifyingContract": config.VALIDATION_REGISTRY_ADDRESS,
        }

        message_types = {
            "TradeIntent": [
                {"name": "action",     "type": "string"},
                {"name": "asset",      "type": "string"},
                {"name": "amountUsd",  "type": "uint256"},
                {"name": "confidence", "type": "uint256"},
                {"name": "timestamp",  "type": "uint256"},
                {"name": "agent",      "type": "address"},
            ],
        }

        message_data = {
            "action":     decision["action"],
            "asset":      decision["asset"],
            "amountUsd":  int(decision["amount_usd"] * 100),   # cents
            "confidence": int(decision["confidence"] * 10000),  # bps
            "timestamp":  int(time.time()),
            "agent":      self.address,
        }

        # encode_typed_data expects (domain, types, primaryType, message)
        signable = encode_typed_data(
            domain_data,
            message_types,
            "TradeIntent",
            message_data,
        )

        signed = self.account.sign_message(signable)
        signature = signed.signature
        intent_hash = signable.body  # 32-byte struct hash

        logger.info(
            "🔏  Signed intent: %s %s $%.2f (conf %.0f%%)",
            decision["action"],
            decision["asset"],
            decision["amount_usd"],
            decision["confidence"] * 100,
        )
        return signature, intent_hash

    def submit_intent(self, decision: dict) -> str:
        """
        Sign a trade intent and submit it to the Validation Registry
        (the on-chain Risk Router).
        """
        signature, intent_hash = self.sign_trade_intent(decision)
        fn = self.validation.functions.submitIntent(signature, intent_hash)
        return self._send_tx(fn)


# ════════════════════════════════════════════════════════════
#  Quick Smoke Test (run file directly)
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    ci = ChainInteractor()
    print(f"Agent address : {ci.address}")
    print(f"Registered    : {ci.is_registered()}")
