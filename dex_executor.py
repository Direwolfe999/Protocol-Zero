"""
Protocol Zero — DEX Executor (Live Uniswap V3 Swaps)
======================================================
Executes real token swaps on Uniswap V3 (Sepolia or Mainnet).

Pipeline position:
  … → Risk Check → EIP-712 Sign → **DEX Execute** → Validation Artifact → …

Supported actions:
  BUY  → swap WETH → USDC  (buy the quote asset)
  SELL → swap USDC → WETH  (sell the quote asset back)

Safety features:
  • DEX_ENABLED flag must be True (off by default)
  • Max slippage protection (default 1%)
  • Deadline protection (5 minute window)
  • Automatic ERC-20 approval before swap
  • Gas estimation with 20% buffer
  • Full logging of every TX for audit trail
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from web3 import Web3
from eth_account import Account

import config
from exceptions import DexExecutionError

logger = logging.getLogger("protocol_zero.dex")
RPC_TIMEOUT_SECONDS: int = 8

# ════════════════════════════════════════════════════════════
#  Uniswap V3 SwapRouter ABI (exactInputSingle only)
# ════════════════════════════════════════════════════════════

SWAP_ROUTER_ABI: list[dict] = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn",           "type": "address"},
                    {"internalType": "address", "name": "tokenOut",          "type": "address"},
                    {"internalType": "uint24",  "name": "fee",              "type": "uint24"},
                    {"internalType": "address", "name": "recipient",         "type": "address"},
                    {"internalType": "uint256", "name": "deadline",          "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn",          "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum",  "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct ISwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
]

# ── ERC-20 ABI (approve + balanceOf + decimals) ───────────

ERC20_ABI: list[dict] = [
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount",  "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "address", "name": "owner",   "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── WETH-specific: deposit (wrap ETH) and withdraw (unwrap) ──

WETH_ABI: list[dict] = ERC20_ABI + [
    {
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "wad", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


# ════════════════════════════════════════════════════════════
#  Data Classes
# ════════════════════════════════════════════════════════════

@dataclass
class SwapResult:
    """Outcome of a DEX swap attempt."""
    success: bool = False
    tx_hash: str = ""
    amount_in: float = 0.0
    amount_out: float = 0.0
    token_in: str = ""
    token_out: str = ""
    gas_used: int = 0
    gas_cost_eth: float = 0.0
    error: str = ""
    block_number: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "gas_used": self.gas_used,
            "gas_cost_eth": self.gas_cost_eth,
            "error": self.error,
            "block_number": self.block_number,
        }


# ════════════════════════════════════════════════════════════
#  DEX Executor
# ════════════════════════════════════════════════════════════

class DexExecutor:
    """
    Executes real token swaps on Uniswap V3.

    Usage:
        dex = DexExecutor()
        result = dex.execute_swap(decision, current_price)
    """

    def __init__(self) -> None:
        # ── Web3 connection ─────────────────────────────
        self.w3 = Web3(
            Web3.HTTPProvider(
                config.RPC_URL,
                request_kwargs={"timeout": RPC_TIMEOUT_SECONDS},
            )
        )
        if not self.w3.is_connected():
            raise DexExecutionError(f"Cannot connect to RPC: {config.RPC_URL}")

        self.account = Account.from_key(config.PRIVATE_KEY)
        self.address = self.account.address

        # ── DEX config ──────────────────────────────────
        self.enabled: bool = getattr(config, "DEX_ENABLED", False)
        self.max_slippage: float = getattr(config, "DEX_MAX_SLIPPAGE_PCT", 1.0) / 100
        self.pool_fee: int = getattr(config, "DEX_POOL_FEE", 3000)  # 0.3%

        # ── Token addresses ─────────────────────────────
        self.weth_address = Web3.to_checksum_address(
            getattr(config, "WETH_ADDRESS", "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14")
        )
        self.usdc_address = Web3.to_checksum_address(
            getattr(config, "USDC_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
        )
        self.router_address = Web3.to_checksum_address(
            getattr(config, "UNISWAP_ROUTER_ADDRESS", "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E")
        )

        # ── Contract handles ────────────────────────────
        self.router = self.w3.eth.contract(
            address=self.router_address, abi=SWAP_ROUTER_ABI
        )
        self.weth = self.w3.eth.contract(
            address=self.weth_address, abi=WETH_ABI
        )
        self.usdc = self.w3.eth.contract(
            address=self.usdc_address, abi=ERC20_ABI
        )

        # ── Token decimals (cache) ──────────────────────
        try:
            self.weth_decimals = self.weth.functions.decimals().call()
        except Exception:
            self.weth_decimals = 18
        try:
            self.usdc_decimals = self.usdc.functions.decimals().call()
        except Exception:
            self.usdc_decimals = 6

        logger.info("🔄  DexExecutor initialized — Router: %s", self.router_address[:10])
        logger.info("    WETH: %s (%d decimals)", self.weth_address[:10], self.weth_decimals)
        logger.info("    USDC: %s (%d decimals)", self.usdc_address[:10], self.usdc_decimals)
        logger.info("    DEX enabled: %s | Slippage: %.1f%% | Pool fee: %d",
                     self.enabled, self.max_slippage * 100, self.pool_fee)

    # ────────────────────────────────────────────────────────
    #  Token Balances
    # ────────────────────────────────────────────────────────

    def get_eth_balance(self) -> float:
        """Get native ETH balance in ETH."""
        wei = self.w3.eth.get_balance(self.address)
        return float(Web3.from_wei(wei, "ether"))

    def get_weth_balance(self) -> float:
        """Get WETH balance in ETH units."""
        raw = self.weth.functions.balanceOf(self.address).call()
        return raw / (10 ** self.weth_decimals)

    def get_usdc_balance(self) -> float:
        """Get USDC balance in USD units."""
        raw = self.usdc.functions.balanceOf(self.address).call()
        return raw / (10 ** self.usdc_decimals)

    def get_balances(self) -> dict:
        """Get all relevant balances."""
        return {
            "eth": self.get_eth_balance(),
            "weth": self.get_weth_balance(),
            "usdc": self.get_usdc_balance(),
            "wallet": self.address,
        }

    # ────────────────────────────────────────────────────────
    #  Internal: send a transaction
    # ────────────────────────────────────────────────────────

    def _send_tx(self, tx: dict) -> dict:
        """Sign, send, and wait for a transaction. Returns the receipt."""
        signed = self.w3.eth.account.sign_transaction(tx, private_key=config.PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info("📤  TX sent: %s", tx_hash.hex())
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] != 1:
            raise DexExecutionError(f"TX reverted: {tx_hash.hex()}")
        logger.info("✅  TX confirmed in block %d (gas used: %d)",
                     receipt["blockNumber"], receipt["gasUsed"])
        return receipt

    # ────────────────────────────────────────────────────────
    #  Wrap ETH → WETH
    # ────────────────────────────────────────────────────────

    def wrap_eth(self, amount_eth: float) -> str:
        """Wrap native ETH into WETH."""
        amount_wei = Web3.to_wei(amount_eth, "ether")
        nonce = self.w3.eth.get_transaction_count(self.address)

        tx = self.weth.functions.deposit().build_transaction({
            "from": self.address,
            "nonce": nonce,
            "value": amount_wei,
            "gas": 60_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": config.CHAIN_ID,
        })

        receipt = self._send_tx(tx)
        logger.info("🔄  Wrapped %.6f ETH → WETH", amount_eth)
        return receipt["transactionHash"].hex()

    # ────────────────────────────────────────────────────────
    #  ERC-20 Approval
    # ────────────────────────────────────────────────────────

    def _ensure_approval(self, token_contract, token_name: str, amount_raw: int) -> None:
        """Approve the SwapRouter to spend tokens if needed."""
        try:
            current_allowance = token_contract.functions.allowance(
                self.address, self.router_address
            ).call()
        except Exception:
            current_allowance = 0

        if current_allowance >= amount_raw:
            logger.info("✅  %s allowance sufficient (%d >= %d)", token_name,
                        current_allowance, amount_raw)
            return

        # Approve max uint256 (one-time infinite approval)
        max_uint = 2**256 - 1
        nonce = self.w3.eth.get_transaction_count(self.address)
        fn = token_contract.functions.approve(self.router_address, max_uint)
        tx = fn.build_transaction({
            "from": self.address,
            "nonce": nonce,
            "gas": 80_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": config.CHAIN_ID,
        })
        self._send_tx(tx)
        logger.info("✅  Approved %s for SwapRouter", token_name)

    # ────────────────────────────────────────────────────────
    #  Core: Execute Swap
    # ────────────────────────────────────────────────────────

    def execute_swap(self, decision: dict, current_price: float = 0.0) -> SwapResult:
        """
        Execute a real Uniswap V3 swap based on the AI decision.

        BUY  → swap WETH for USDC (convert ETH holdings into stablecoin position)
        SELL → swap USDC for WETH (exit stablecoin back to ETH)

        Parameters
        ----------
        decision       : dict with action, amount_usd, asset, etc.
        current_price  : current ETH price in USD (for amount conversion)

        Returns
        -------
        SwapResult with success status, tx hash, amounts, gas info
        """
        result = SwapResult()
        action = decision.get("action", "HOLD")

        # ── Safety checks ─────────────────────────────
        if action == "HOLD":
            result.error = "HOLD — no swap needed"
            return result

        if not self.enabled:
            result.error = "DEX execution disabled (set DEX_ENABLED=true in .env)"
            logger.warning("⚠️  %s", result.error)
            return result

        amount_usd = decision.get("amount_usd", 0)
        if amount_usd <= 0:
            result.error = "Amount is zero — nothing to swap"
            return result

        # ── Determine swap direction ──────────────────
        if action == "BUY":
            # Buy position: WETH → USDC
            token_in = self.weth_address
            token_out = self.usdc_address
            token_in_contract = self.weth
            token_in_name = "WETH"
            decimals_in = self.weth_decimals
            decimals_out = self.usdc_decimals

            # Convert USD amount to WETH amount
            if current_price <= 0:
                result.error = "Cannot convert USD to WETH — price unknown"
                return result
            amount_tokens = amount_usd / current_price
            amount_raw = int(amount_tokens * (10 ** decimals_in))

            # Check WETH balance (wrap ETH if needed)
            weth_balance = self.get_weth_balance()
            if weth_balance < amount_tokens:
                eth_balance = self.get_eth_balance()
                needed = amount_tokens - weth_balance
                if eth_balance > needed + 0.01:  # keep 0.01 ETH for gas
                    logger.info("🔄  Wrapping %.6f ETH to cover swap", needed)
                    try:
                        self.wrap_eth(needed)
                    except Exception as e:
                        result.error = f"Failed to wrap ETH: {e}"
                        return result
                else:
                    result.error = (f"Insufficient balance: need {amount_tokens:.6f} WETH, "
                                    f"have {weth_balance:.6f} WETH + {eth_balance:.6f} ETH")
                    return result

            # Min output (USDC with slippage)
            expected_out = amount_usd  # 1 USDC ≈ 1 USD
            min_out_raw = int(expected_out * (1 - self.max_slippage) * (10 ** decimals_out))

        elif action == "SELL":
            # Sell position: USDC → WETH
            token_in = self.usdc_address
            token_out = self.weth_address
            token_in_contract = self.usdc
            token_in_name = "USDC"
            decimals_in = self.usdc_decimals
            decimals_out = self.weth_decimals

            amount_tokens = amount_usd  # USDC is 1:1 USD
            amount_raw = int(amount_tokens * (10 ** decimals_in))

            # Check USDC balance
            usdc_balance = self.get_usdc_balance()
            if usdc_balance < amount_tokens:
                result.error = (f"Insufficient USDC: need {amount_tokens:.2f}, "
                                f"have {usdc_balance:.2f}")
                return result

            # Min output (WETH with slippage)
            if current_price <= 0:
                result.error = "Cannot calculate min output — price unknown"
                return result
            expected_out = amount_usd / current_price
            min_out_raw = int(expected_out * (1 - self.max_slippage) * (10 ** decimals_out))

        else:
            result.error = f"Unknown action: {action}"
            return result

        result.token_in = token_in_name
        result.token_out = "USDC" if action == "BUY" else "WETH"
        result.amount_in = amount_tokens

        # ── Approve token spending ────────────────────
        try:
            self._ensure_approval(token_in_contract, token_in_name, amount_raw)
        except Exception as e:
            result.error = f"Approval failed: {e}"
            return result

        # ── Build swap transaction ────────────────────
        deadline = int(time.time()) + 300  # 5 minutes
        nonce = self.w3.eth.get_transaction_count(self.address)

        swap_params = (
            token_in,               # tokenIn
            token_out,              # tokenOut
            self.pool_fee,          # fee tier (3000 = 0.3%)
            self.address,           # recipient
            deadline,               # deadline
            amount_raw,             # amountIn
            min_out_raw,            # amountOutMinimum
            0,                      # sqrtPriceLimitX96 (0 = no limit)
        )

        try:
            fn = self.router.functions.exactInputSingle(swap_params)

            # Estimate gas
            try:
                gas_estimate = fn.estimate_gas({"from": self.address})
                gas_limit = int(gas_estimate * 1.2)  # 20% buffer
            except Exception:
                gas_limit = 300_000  # fallback

            tx = fn.build_transaction({
                "from": self.address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": config.CHAIN_ID,
                "value": 0,
            })

            # ── Execute ──────────────────────────────
            logger.info("🔄  Swapping %.6f %s → %s (min out: %s, deadline: %d)",
                        amount_tokens, token_in_name, result.token_out,
                        min_out_raw, deadline)

            receipt = self._send_tx(tx)

            result.success = True
            result.tx_hash = receipt["transactionHash"].hex()
            result.gas_used = receipt["gasUsed"]
            result.gas_cost_eth = float(Web3.from_wei(
                receipt["gasUsed"] * receipt.get("effectiveGasPrice", self.w3.eth.gas_price),
                "ether"
            ))
            result.block_number = receipt["blockNumber"]

            # Try to get actual output amount from logs
            # (simplified — just recalculate from expected)
            result.amount_out = expected_out

            logger.info("✅  Swap complete! TX: %s | Gas: %.6f ETH",
                        result.tx_hash[:20], result.gas_cost_eth)

        except Exception as e:
            result.error = f"Swap failed: {e}"
            logger.error("❌  Swap failed: %s", e)

        return result

    # ────────────────────────────────────────────────────────
    #  Convenience: full status check
    # ────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return full DEX executor status for dashboard."""
        balances = self.get_balances()
        return {
            "enabled": self.enabled,
            "router": self.router_address,
            "weth": self.weth_address,
            "usdc": self.usdc_address,
            "pool_fee": self.pool_fee,
            "max_slippage_pct": self.max_slippage * 100,
            "chain_id": config.CHAIN_ID,
            **balances,
        }


# ════════════════════════════════════════════════════════════
#  Quick Test
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    dex = DexExecutor()
    print("DEX Status:", dex.status())
