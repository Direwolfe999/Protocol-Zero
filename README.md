# 🛡️ Protocol Zero — Autonomous ERC-8004 DeFi Trading Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![ERC-8004](https://img.shields.io/badge/standard-ERC--8004-blueviolet.svg)](https://eips.ethereum.org/EIPS/eip-8004)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Capital preservation first, profit second.**

Protocol Zero is a trust-minimized, autonomous DeFi trading agent built on the
[ERC-8004](https://eips.ethereum.org/EIPS/eip-8004) standard for on-chain agent
identity, reputation, and validation. It combines AI-driven market reasoning
(Amazon Bedrock Nova) with cryptographic accountability (EIP-712 signed intents)
and a multi-layered risk management pipeline.

---

## Architecture

```
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
                 └──────────────┘                 └───────────────────┘
```

### Core Modules

| Module | Purpose |
|---|---|
| `brain.py` | AI reasoning engine — fetches OHLCV data, builds prompts, calls Nova Lite with agentic tool-use |
| `risk_check.py` | 6-layer fail-closed risk gate (position size, daily loss, frequency, concentration, confidence, expiry) |
| `sign_trade.py` | EIP-712 trade intent validation & signing — the AI never touches private keys |
| `eip712_signer.py` | Pure cryptographic EIP-712 module — no RPC required |
| `chain_interactor.py` | Web3 bridge for the three ERC-8004 registries (Identity, Reputation, Validation) |
| `dex_executor.py` | Live Uniswap V3 swap execution with slippage protection |
| `dashboard.py` | Streamlit cinematic dashboard with cognitive stream, market orb, trade DNA, risk heatmap |
| `config.py` | Centralized configuration — loads `.env` with validation |
| `metadata_handler.py` | ERC-8004 `agent-identity.json` generator with keccak256 & IPFS CID hashing |
| `performance_tracker.py` | Session analytics — Sharpe ratio, win rate, drawdown tracking |
| `validation_artifacts.py` | Cryptographic audit trail builder for every decision |

### Nova AI Integrations

| Module | AWS Service | Purpose |
|---|---|---|
| `brain.py` | Bedrock (Nova 2 Lite) | Agentic market reasoning with tool-use |
| `nova_sonic_voice.py` | Nova 2 Sonic | Bidirectional voice interface for trading commands |
| `nova_act_auditor.py` | Nova Act | Browser-based smart contract auditing |
| `nova_embeddings.py` | Nova Multimodal Embeddings | Scam-pattern detection on token metadata |

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Direwolfe999/Protocol-Zero.git
cd Protocol-Zero
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your real keys
```

**Required variables:**
- `RPC_URL` — Sepolia or mainnet RPC endpoint (Alchemy / Infura)
- `PRIVATE_KEY` — Bot wallet private key (hex, no `0x` prefix)
- `IDENTITY_REGISTRY_ADDRESS` — ERC-8004 Identity Registry contract
- `REPUTATION_REGISTRY_ADDRESS` — ERC-8004 Reputation Registry contract
- `VALIDATION_REGISTRY_ADDRESS` — ERC-8004 Validation Registry contract

**Optional (for full AI reasoning):**
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — Amazon Bedrock credentials
- `DEX_ENABLED=true` — Enable live Uniswap V3 swaps

### 3. Register Agent (one-time)

```bash
python main.py --register
```

### 4. Run

```bash
# Single decision cycle
python main.py

# Continuous trading loop
python main.py --loop

# Launch the dashboard
streamlit run dashboard.py
```

---

## Risk Management

Protocol Zero enforces a **fail-closed** risk pipeline — if any check is uncertain,
the trade is blocked. Six independent checks run in sequence:

| Check | Purpose | Default Limit |
|---|---|---|
| `check_max_position_size` | Single-trade USD cap | $500 |
| `check_daily_loss_limit` | Cumulative daily drawdown | -$1,000 |
| `check_trade_frequency` | Max trades per rolling hour | 10 |
| `check_concentration` | Max % of capital in one asset | 30% |
| `check_confidence_floor` | Minimum model confidence | 40% |
| `check_intent_expiry` | Reject stale intents | 5 min TTL |

---

## ERC-8004 Compliance

Protocol Zero implements all three ERC-8004 registries:

- **Identity Registry** — Agent mints an ERC-721 NFT with `register(agentURI)`, stores metadata via `setMetadata`
- **Reputation Registry** — Every trade result is logged via `giveFeedback()` with PnL, tags, and content hashes
- **Validation Registry** — Trade intents are submitted via `validationRequest()` with EIP-712 signatures

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run a specific module's smoke test
python risk_check.py
python eip712_signer.py
python sign_trade.py --json '{"action":"BUY","asset":"ETH","confidence":0.8,"risk_score":3,"position_size_percent":1.0,"stop_loss_percent":3.0,"take_profit_percent":6.0,"market_regime":"TRENDING"}'
```

---

## Project Structure

```
Protocol-Zero/
├── brain.py                  # AI reasoning engine (Nova Lite + tool-use)
├── chain_interactor.py       # Web3 bridge for ERC-8004 registries
├── config.py                 # Centralized .env loader with validation
├── dashboard.py              # Streamlit cinematic dashboard
├── dex_executor.py           # Uniswap V3 live swap execution
├── eip712_signer.py          # EIP-712 structured data signing
├── exceptions.py             # Custom exception hierarchy
├── main.py                   # Orchestrator — full agent lifecycle
├── metadata_handler.py       # ERC-8004 agent-identity.json generator
├── nova_act_auditor.py       # Nova Act browser-based contract auditing
├── nova_embeddings.py        # Nova multimodal embedding scam detection
├── nova_sonic_voice.py       # Nova Sonic bidirectional voice interface
├── performance_tracker.py    # Session analytics (Sharpe, drawdown, etc.)
├── requirements.txt          # Python dependencies
├── risk_check.py             # 6-layer fail-closed risk gate
├── sign_trade.py             # Trade intent validator & signer
├── validation_artifacts.py   # Cryptographic audit trail builder
├── tests/                    # Unit & integration tests
│   ├── test_risk_check.py
│   ├── test_brain.py
│   └── test_sign_trade.py
├── .env.example              # Environment variable template
├── .gitignore                # Git exclusions
└── README.md                 # This file
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*Built for the ERC-8004 Autonomous Agents Hackathon.*
