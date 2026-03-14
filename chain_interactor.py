"""
Protocol Zero — Chain Interactor (Blockchain Bridge)
=====================================================
Responsibilities:
  1. Connect to an EVM chain via Web3.
  2. Register the agent on the ERC-8004 Identity Registry via register(agentURI).
  3. Submit feedback to the Reputation Registry via giveFeedback().
  4. Sign trade intents using EIP-712 structured data.
  5. Submit validation requests to the Validation Registry via validationRequest().

ERC-8004 Standard — Three Registries:
  • Identity Registry   — ERC-721 NFT with register(agentURI), setMetadata, getMetadata, setAgentWallet.
  • Reputation Registry — giveFeedback(agentId, value, valueDecimals, tag1, tag2, endpoint, feedbackURI, feedbackHash).
  • Validation Registry — validationRequest(validatorAddress, agentId, requestURI, requestHash) +
                           validationResponse(requestId, status, responseURI, responseHash, reason).

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
from exceptions import ChainError, RegistryError, TransactionError

logger = logging.getLogger("protocol_zero.chain")

# ── Retry config ──────────────────────────────────────────
MAX_TX_RETRIES: int = 3
RETRY_BASE_DELAY: float = 2.0  # seconds — exponential backoff base
RPC_TIMEOUT_SECONDS: int = 8

# ════════════════════════════════════════════════════════════
#  ERC-8004 Compliant ABIs for the Three Registries
# ════════════════════════════════════════════════════════════

IDENTITY_REGISTRY_ABI: list[dict] = [
    # register(string agentURI) → uint256 agentId
    {
        "inputs": [{"internalType": "string", "name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # setMetadata(uint256 agentId, string key, string value)
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "string", "name": "key", "type": "string"},
            {"internalType": "string", "name": "value", "type": "string"},
        ],
        "name": "setMetadata",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # getMetadata(uint256 agentId, string key) → string value
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "string", "name": "key", "type": "string"},
        ],
        "name": "getMetadata",
        "outputs": [{"internalType": "string", "name": "value", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    # setAgentWallet(uint256 agentId, address wallet)
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "address", "name": "wallet", "type": "address"},
        ],
        "name": "setAgentWallet",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # getAgentWallet(uint256 agentId) → address
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "getAgentWallet",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    # ownerOf(uint256 tokenId) → address (ERC-721)
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    # balanceOf(address owner) → uint256 (ERC-721 — check if registered)
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    # tokenOfOwnerByIndex(address owner, uint256 index) → uint256 (get agent's token ID)
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "uint256", "name": "index", "type": "uint256"},
        ],
        "name": "tokenOfOwnerByIndex",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

REPUTATION_REGISTRY_ABI: list[dict] = [
    # giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
    #              string tag1, string tag2, string endpoint,
    #              string feedbackURI, bytes32 feedbackHash)
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "int128", "name": "value", "type": "int128"},
            {"internalType": "uint8", "name": "valueDecimals", "type": "uint8"},
            {"internalType": "string", "name": "tag1", "type": "string"},
            {"internalType": "string", "name": "tag2", "type": "string"},
            {"internalType": "string", "name": "endpoint", "type": "string"},
            {"internalType": "string", "name": "feedbackURI", "type": "string"},
            {"internalType": "bytes32", "name": "feedbackHash", "type": "bytes32"},
        ],
        "name": "giveFeedback",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # getSummary(uint256 agentId) → (uint256 totalFeedback, int256 cumulativeValue, uint256 positiveCount, uint256 negativeCount)
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "getSummary",
        "outputs": [
            {"internalType": "uint256", "name": "totalFeedback", "type": "uint256"},
            {"internalType": "int256", "name": "cumulativeValue", "type": "int256"},
            {"internalType": "uint256", "name": "positiveCount", "type": "uint256"},
            {"internalType": "uint256", "name": "negativeCount", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    # readFeedback(uint256 agentId, uint256 index) → tuple
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "uint256", "name": "index", "type": "uint256"},
        ],
        "name": "readFeedback",
        "outputs": [
            {"internalType": "address", "name": "sender", "type": "address"},
            {"internalType": "int128", "name": "value", "type": "int128"},
            {"internalType": "string", "name": "tag1", "type": "string"},
            {"internalType": "string", "name": "tag2", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    # getClients(uint256 agentId) → address[]
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "getClients",
        "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function",
    },
]

VALIDATION_REGISTRY_ABI: list[dict] = [
    # validationRequest(address validatorAddress, uint256 agentId, string requestURI, bytes32 requestHash) → bytes32 requestId
    {
        "inputs": [
            {"internalType": "address", "name": "validatorAddress", "type": "address"},
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "string", "name": "requestURI", "type": "string"},
            {"internalType": "bytes32", "name": "requestHash", "type": "bytes32"},
        ],
        "name": "validationRequest",
        "outputs": [{"internalType": "bytes32", "name": "requestId", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # validationResponse(bytes32 requestId, uint8 status, string responseURI, bytes32 responseHash, string reason)
    {
        "inputs": [
            {"internalType": "bytes32", "name": "requestId", "type": "bytes32"},
            {"internalType": "uint8", "name": "status", "type": "uint8"},
            {"internalType": "string", "name": "responseURI", "type": "string"},
            {"internalType": "bytes32", "name": "responseHash", "type": "bytes32"},
            {"internalType": "string", "name": "reason", "type": "string"},
        ],
        "name": "validationResponse",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # getValidationStatus(bytes32 requestId) → uint8 status
    {
        "inputs": [{"internalType": "bytes32", "name": "requestId", "type": "bytes32"}],
        "name": "getValidationStatus",
        "outputs": [{"internalType": "uint8", "name": "status", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    # getSummary(uint256 agentId) → (uint256 totalRequests, uint256 approved, uint256 rejected)
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "getSummary",
        "outputs": [
            {"internalType": "uint256", "name": "totalRequests", "type": "uint256"},
            {"internalType": "uint256", "name": "approved", "type": "uint256"},
            {"internalType": "uint256", "name": "rejected", "type": "uint256"},
        ],
        "stateMutability": "view",
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
        self.w3 = Web3(
            Web3.HTTPProvider(
                config.RPC_URL,
                request_kwargs={"timeout": RPC_TIMEOUT_SECONDS},
            )
        )
        # Support PoA chains (Polygon, BSC, testnets …)
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            raise ChainError(
                f"Cannot reach RPC: {config.RPC_URL}",
                details={"rpc_url": config.RPC_URL},
            )
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

        # ── Agent ID cache ────────────────────────────────
        self._agent_id: int | None = None

    # ────────────────────────────────────────────────────────
    #  Internal: build, sign & send a transaction
    # ────────────────────────────────────────────────────────

    def _send_tx(self, fn_call) -> str:
        """
        Build, sign, and broadcast a contract function call.
        Retries with exponential backoff on transient failures.
        Returns the transaction hash hex string.
        """
        last_error: Exception | None = None

        for attempt in range(1, MAX_TX_RETRIES + 1):
            try:
                nonce = self.w3.eth.get_transaction_count(self.address)
                gas_price = self.w3.eth.gas_price

                # Estimate gas dynamically (proxy contracts need more than static 300k)
                try:
                    estimated = fn_call.estimate_gas({"from": self.address})
                    gas_limit = int(estimated * 1.5) + 50_000  # 1.5× + 50k buffer
                except Exception:
                    gas_limit = 500_000  # safe fallback

                tx = fn_call.build_transaction({
                    "from": self.address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "chainId": config.CHAIN_ID,
                })
                signed = self.w3.eth.account.sign_transaction(tx, private_key=config.PRIVATE_KEY)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                logger.info("📤  TX sent (attempt %d/%d): %s", attempt, MAX_TX_RETRIES, tx_hash.hex())

                # Wait for receipt (timeout 120 s)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] != 1:
                    raise TransactionError(
                        f"TX reverted: {tx_hash.hex()}",
                        details={"tx_hash": tx_hash.hex(), "block": receipt.get("blockNumber")},
                    )
                logger.info("✅  TX confirmed in block %s", receipt["blockNumber"])
                return tx_hash.hex()

            except TransactionError:
                raise  # Don't retry on-chain reverts — they'll revert again
            except Exception as e:
                last_error = e
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "TX attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt, MAX_TX_RETRIES, e, delay,
                )
                if attempt < MAX_TX_RETRIES:
                    time.sleep(delay)

        raise TransactionError(
            f"TX failed after {MAX_TX_RETRIES} attempts: {last_error}",
            details={"last_error": str(last_error)},
        )

    # ────────────────────────────────────────────────────────
    #  1.  Identity Registry — register / check agent (ERC-8004)
    # ────────────────────────────────────────────────────────

    def is_registered(self) -> bool:
        """Check if this wallet owns an ERC-8004 Identity NFT."""
        try:
            balance = self.identity.functions.balanceOf(self.address).call()
            return balance > 0
        except Exception:
            logger.warning("balanceOf call failed — assuming not registered.")
            return False

    def register_agent(self, agent_uri: str = "") -> str:
        """
        Register on the ERC-8004 Identity Registry via register(agentURI).
        The agentURI points to the agent-identity.json metadata.
        Idempotent: skips if already registered.
        """
        if self.is_registered():
            logger.info("Agent already registered on Identity Registry.")
            return ""
        if not agent_uri:
            agent_uri = f"https://protocol-zero.agent/{config.AGENT_HANDLE}"
        logger.info("📝  Registering agent with URI '%s' …", agent_uri)
        fn = self.identity.functions.register(agent_uri)
        return self._send_tx(fn)

    def get_token_id(self) -> int:
        """Return the NFT token ID (agentId) for this agent."""
        if self._agent_id is not None:
            return self._agent_id
        try:
            token_id = self.identity.functions.tokenOfOwnerByIndex(self.address, 0).call()
            self._agent_id = token_id
            return token_id
        except Exception:
            # Some identity contracts are not ERC-721 enumerable.
            # Fallback: discover token id from Transfer logs to this wallet.
            token_id = self._discover_token_id_from_logs()
            if token_id > 0:
                self._agent_id = token_id
                return token_id
            logger.debug("Agent token ID not available (agent may not be registered yet).")
            return 0

    def _discover_token_id_from_logs(self) -> int:
        """Best-effort token ID discovery using ERC-721 Transfer logs."""
        try:
            latest = int(self.w3.eth.block_number)
            topic0 = Web3.keccak(text="Transfer(address,address,uint256)")
            to_topic = "0x" + self.address.lower().replace("0x", "").rjust(64, "0")

            # Progressive windows to reduce RPC load on fast paths
            for window in (120_000, 400_000, 1_200_000):
                from_block = max(0, latest - window)
                logs = self.w3.eth.get_logs({
                    "address": self.identity.address,
                    "fromBlock": from_block,
                    "toBlock": "latest",
                    "topics": [topic0, None, to_topic],
                })
                for lg in reversed(logs):
                    topics = lg.get("topics", [])
                    if len(topics) < 4:
                        continue
                    token_id = int(topics[3].hex(), 16)
                    try:
                        owner = self.identity.functions.ownerOf(token_id).call()
                        if owner and owner.lower() == self.address.lower():
                            return token_id
                    except Exception:
                        continue
        except Exception as e:
            logger.debug("Token ID discovery from logs failed: %s", e)
        return 0

    def set_metadata(self, key: str, value: str) -> str:
        """Set a metadata key-value pair on the Identity Registry."""
        agent_id = self.get_token_id()
        fn = self.identity.functions.setMetadata(agent_id, key, value)
        return self._send_tx(fn)

    def get_metadata(self, key: str) -> str:
        """Get a metadata value from the Identity Registry."""
        agent_id = self.get_token_id()
        return self.identity.functions.getMetadata(agent_id, key).call()

    # ────────────────────────────────────────────────────────
    #  2.  Reputation Registry — giveFeedback (ERC-8004)
    # ────────────────────────────────────────────────────────

    def give_feedback(
        self,
        value: int,
        value_decimals: int = 2,
        tag1: str = "TRADE",
        tag2: str = "",
        endpoint: str = "",
        feedback_uri: str = "",
        feedback_hash: bytes = b"\x00" * 32,
    ) -> str:
        """
        Submit feedback to the Reputation Registry via giveFeedback().

        Parameters
        ----------
        value           : int128 feedback value (e.g., PnL in basis points)
        value_decimals  : uint8 number of decimals in value
        tag1            : Primary category tag (e.g., "TRADE", "RISK")
        tag2            : Secondary tag (e.g., "BUY", "SELL")
        endpoint        : The endpoint/service that generated this action
        feedback_uri    : URI pointing to detailed feedback data
        feedback_hash   : bytes32 hash of the feedback content
        """
        agent_id = self.get_token_id()
        logger.info("📊  Giving feedback: value=%d tag1=%s tag2=%s", value, tag1, tag2)
        fn = self.reputation.functions.giveFeedback(
            agent_id,
            value,
            value_decimals,
            tag1,
            tag2,
            endpoint,
            feedback_uri,
            feedback_hash,
        )
        return self._send_tx(fn)

    def log_trade_result(
        self,
        action_type: str,
        pnl_bps: int,
        metadata: str = "",
    ) -> str:
        """
        Log a trade result as reputation feedback.
        Convenience wrapper around giveFeedback().

        Parameters
        ----------
        action_type : str   "BUY", "SELL", "HOLD"
        pnl_bps     : int   Profit/loss in basis points (+150 = +1.5%)
        metadata    : str   JSON blob for context
        """
        # Compute feedback hash from metadata
        feedback_hash = b"\x00" * 32
        if metadata:
            feedback_hash = Web3.keccak(text=metadata)

        return self.give_feedback(
            value=pnl_bps,
            value_decimals=2,
            tag1="TRADE",
            tag2=action_type,
            endpoint="protocol-zero/brain",
            feedback_uri=metadata,
            feedback_hash=feedback_hash,
        )

    def get_reputation_summary(self) -> dict:
        """Query cumulative reputation summary for this agent."""
        agent_id = self.get_token_id()
        try:
            total, cumulative, positive, negative = (
                self.reputation.functions.getSummary(agent_id).call()
            )
            return {
                "total_feedback": total,
                "cumulative_value": cumulative,
                "positive_count": positive,
                "negative_count": negative,
            }
        except Exception:
            return {"total_feedback": 0, "cumulative_value": 0,
                    "positive_count": 0, "negative_count": 0}

    # ────────────────────────────────────────────────────────
    #  3.  Validation Registry — ERC-8004 validationRequest/Response
    # ────────────────────────────────────────────────────────

    _ZERO_ADDR = "0x" + "0" * 40

    def submit_validation_request(
        self,
        validator_address: str,
        agent_id: int,
        request_uri: str,
        request_hash: bytes,
    ) -> str:
        """
        Submit a validation request to the Validation Registry.

        Parameters
        ----------
        validator_address : Address of the validator contract
        agent_id         : The agent's NFT token ID
        request_uri      : URI pointing to the validation artifact
        request_hash     : bytes32 hash of the request content
        """
        if config.VALIDATION_REGISTRY_ADDRESS == self._ZERO_ADDR:
            logger.info("📋  Validation Registry not deployed — recording locally.")
            return "0x" + Web3.keccak(text=request_uri).hex()
        logger.info("📋  Submitting validation request to %s …", validator_address[:10])
        fn = self.validation.functions.validationRequest(
            Web3.to_checksum_address(validator_address),
            agent_id,
            request_uri,
            request_hash,
        )
        return self._send_tx(fn)

    def get_validation_status(self, request_id: bytes) -> int:
        """Check the status of a validation request."""
        if config.VALIDATION_REGISTRY_ADDRESS == self._ZERO_ADDR:
            return 0
        return self.validation.functions.getValidationStatus(request_id).call()

    def get_validation_summary(self) -> dict:
        """Get validation summary for this agent."""
        if config.VALIDATION_REGISTRY_ADDRESS == self._ZERO_ADDR:
            return {"total_requests": 0, "approved": 0, "rejected": 0}
        agent_id = self.get_token_id()
        try:
            total, approved, rejected = (
                self.validation.functions.getSummary(agent_id).call()
            )
            return {
                "total_requests": total,
                "approved": approved,
                "rejected": rejected,
            }
        except Exception:
            return {"total_requests": 0, "approved": 0, "rejected": 0}

    # ────────────────────────────────────────────────────────
    #  4.  EIP-712 Trade Intent Signing
    # ────────────────────────────────────────────────────────

    def sign_trade_intent(self, decision: dict) -> tuple[bytes, bytes]:
        """
        Create an EIP-712 typed-data signature for a trade intent.

        Parameters
        ----------
        decision : dict with keys action, asset, amount_usd, confidence, risk_score

        Returns
        -------
        (signature_bytes, intent_hash_bytes32)
        """
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
                {"name": "riskScore",  "type": "uint256"},
                {"name": "timestamp",  "type": "uint256"},
                {"name": "agent",      "type": "address"},
            ],
            "EIP712Domain": [
                {"name": "name",              "type": "string"},
                {"name": "version",           "type": "string"},
                {"name": "chainId",           "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        }

        message_data = {
            "action":     decision["action"],
            "asset":      decision["asset"],
            "amountUsd":  int(decision.get("amount_usd", 0) * 100),   # cents
            "confidence": int(decision.get("confidence", 0) * 10000),  # bps
            "riskScore":  int(decision.get("risk_score", 5)),
            "timestamp":  int(time.time()),
            "agent":      self.address,
        }

        signable = encode_typed_data(
            full_message={
                "types":       message_types,
                "primaryType": "TradeIntent",
                "domain":      domain_data,
                "message":     message_data,
            }
        )

        signed = self.account.sign_message(signable)
        signature = signed.signature
        intent_hash = signable.body  # 32-byte struct hash

        logger.info(
            "🔏  Signed intent: %s %s $%.2f (conf %.0f%% risk %d)",
            decision["action"],
            decision["asset"],
            decision.get("amount_usd", 0),
            decision.get("confidence", 0) * 100,
            decision.get("risk_score", 5),
        )
        return signature, intent_hash

    def submit_intent(self, decision: dict) -> str:
        """
        Sign a trade intent and submit it via validationRequest().
        If the Validation Registry is not deployed (zero address),
        the intent is signed locally and a deterministic hash returned.
        """
        signature, intent_hash = self.sign_trade_intent(decision)

        # Graceful fallback when no Validation Registry is deployed
        if config.VALIDATION_REGISTRY_ADDRESS == self._ZERO_ADDR:
            logger.info("📋  Validation Registry not deployed — intent signed locally.")
            request_uri = json.dumps(decision, default=str)
            return "0x" + Web3.keccak(text=request_uri).hex()

        agent_id = self.get_token_id()
        request_uri = json.dumps(decision, default=str)
        request_hash = Web3.keccak(text=request_uri)

        validator = config.VALIDATOR_ADDRESS or config.VALIDATION_REGISTRY_ADDRESS

        fn = self.validation.functions.validationRequest(
            Web3.to_checksum_address(validator),
            agent_id,
            request_uri,
            request_hash,
        )
        return self._send_tx(fn)


# ════════════════════════════════════════════════════════════
#  Quick Smoke Test (run file directly)
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    ci = ChainInteractor()
    print(f"Agent address : {ci.address}")
    print(f"Registered    : {ci.is_registered()}")
    print(f"Reputation    : {ci.get_reputation_summary()}")
    print(f"Validation    : {ci.get_validation_summary()}")
