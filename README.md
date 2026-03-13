---
title: Protocol Zero
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 🛡️ Protocol Zero — Autonomous ERC-8004 DeFi Trading Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![ERC-8004](https://img.shields.io/badge/standard-ERC--8004-blueviolet.svg)](https://eips.ethereum.org/EIPS/eip-8004)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Amazon Nova](https://img.shields.io/badge/AI-Amazon%20Nova-orange.svg)](https://aws.amazon.com/bedrock/)

> **Capital preservation first, profit second.**

Protocol Zero is a trust-minimized, autonomous DeFi trading agent built on the
[ERC-8004](https://eips.ethereum.org/EIPS/eip-8004) standard for on-chain agent
identity, reputation, and validation. It combines AI-driven market reasoning
(Amazon Bedrock Nova) with cryptographic accountability (EIP-712 signed intents)
and a multi-layered risk management pipeline.

---

## 🎬 Demo

> **📺 Demo Video** — *Coming soon before final submission.*
>
> Run `streamlit run streamlit_app.py` to see Protocol Zero live: AI-driven market analysis, EIP-712 intent signing, and on-chain ERC-8004 registration — all in one cinematic dashboard.

---

## 📸 Screenshots

> Run `streamlit run streamlit_app.py` to experience the full cinematic dashboard: cognitive stream, market regime orb, trade DNA, risk heat-map, XAI reasoning panel, and more.
>
> *Screenshots will be added before final submission.*

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

| Module | AWS Service | Purpose | Live / Fallback |
|---|---|---|---|
| `brain.py` | Bedrock (Nova Lite) | Agentic market reasoning with tool-use loop | ✅ Real Converse API |
| `nova_sonic_voice.py` | Bedrock (Nova Lite) | Text intelligence for voice commands (browser TTS) | ⚡ Nova Lite text + Web Speech API |
| `nova_act_auditor.py` | Nova Act (invite-only) | Browser-based smart contract auditing | ⬇️ Simulated (SDK invite-only) |
| `nova_embeddings.py` | Nova Embed Multimodal | Scam-pattern detection via cosine similarity | ✅ Real embeddings / heuristic fallback |

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
streamlit run streamlit_app.py
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

### Test Coverage

| Module | Test File | Coverage |
|---|---|---|
| `brain.py` | `tests/test_brain.py` | Rule-based engine, response parser |
| `risk_check.py` | `tests/test_risk_check.py` | All 6 risk gates |
| `sign_trade.py` | `tests/test_sign_trade.py` | Intent validation & signing |
| `eip712_signer.py` | `tests/test_eip712_signer.py` | EIP-712 message builder, signing, nonce persistence |
| `nova_sonic_voice.py` | `tests/test_nova_sonic_voice.py` | Command parser, text fallback, alerts |
| `performance_tracker.py` | `tests/test_performance_tracker.py` | Sharpe, drawdown, win rate |
| `metadata_handler.py` | `tests/test_metadata_handler.py` | Metadata generation & hashing |
| `validation_artifacts.py` | `tests/test_validation_artifacts.py` | Artifact data structures |
| `exceptions.py` | `tests/test_exceptions.py` | Exception hierarchy |

---

## 🤖 Amazon Nova AI Integration

Protocol Zero integrates **four** Amazon Nova services through Bedrock,
with transparent fallback engines for each:

### Nova Lite — Agentic Market Reasoning ✅
The brain uses the Bedrock **Converse API** with tool-use to make trading decisions.
The LLM can request additional data mid-reasoning by calling tools:
- `rug_pull_scanner` → Check contracts for scam indicators
- `market_deep_dive` → Fetch real-time order-book depth from CCXT
- `nova_act_audit` → Browser-based contract verification
- `embedding_scan` → Scam-pattern detection on token metadata

**This is the strongest integration — a real agentic loop with tool orchestration.**

### Nova Voice Intelligence ⚡
Uses **Nova Lite Converse API** for intelligent text responses to voice commands.
Browser-side **Web Speech API** handles text-to-speech playback.
A Nova Sonic bidirectional stream session is initialised for future audio I/O,
but audio frame processing is not yet wired.
Falls back to rule-based text responses when AWS is unavailable.

### Nova Act — Browser-Based Smart Contract Auditing ⬇️
The code implements real Nova Act browser automation for Etherscan/DEXTools
auditing. However, the `nova-act` SDK is **invite-only** and not publicly
available. The system falls back to deterministic heuristic audits that
honestly label themselves as `"audit_method": "simulated"`.

### Nova Multimodal Embeddings — Scam Detection ✅
Generates real embeddings via `amazon.nova-embed-multimodal-v1:0` and
compares them against reference pattern vectors using **cosine similarity**.
Falls back to keyword/hash heuristics when AWS is unavailable.

> All Nova services are **optional** — the system gracefully falls back
> to rule-based engines and text-mode responses when AWS credentials
> are not configured. Fallback modes are clearly labeled in the dashboard.

---

## 🔧 Troubleshooting

### "AWS credentials not ready — using rule-based fallback brain"
This is normal when `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` are not set.
The system uses a technical-indicator-driven fallback engine (RSI + SMA crossovers).

### "Cannot reach RPC" error
Check your `RPC_URL` in `.env`. For local testing, start Anvil:
```bash
anvil --chain-id 31337
```
Then set `RPC_URL=http://127.0.0.1:8545` in `.env.local`.

### "nova-act" install fails
`nova-act` is an invite-only SDK. It's commented out of `requirements.txt`.
Install it manually if you have access: `pip install nova-act`.
The system falls back to simulated audits when unavailable.

### Dashboard won't start
```bash
# Make sure Streamlit is installed
pip install streamlit plotly

# Run from the project root
streamlit run streamlit_app.py --server.port 8502
```

### EIP-712 signature mismatch
Ensure `CHAIN_ID` and `VALIDATION_REGISTRY_ADDRESS` in your `.env` match
the values hard-coded in your deployed contract. The EIP-712 domain separator
must be identical on both sides.

---

## Project Structure

```
Protocol-Zero/
├── brain.py                  # AI reasoning engine (Nova Lite + tool-use)
├── chain_interactor.py       # Web3 bridge for ERC-8004 registries
├── config.py                 # Centralized .env loader with validation
├── dashboard.py              # Streamlit cinematic dashboard
├── streamlit_app.py          # Streamlit Cloud entrypoint (main module)
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
├── pyproject.toml            # Project metadata & optional dependencies
├── risk_check.py             # 6-layer fail-closed risk gate
├── sign_trade.py             # Trade intent validator & signer
├── validation_artifacts.py   # Cryptographic audit trail builder
├── tests/                    # Unit & integration tests
│   ├── test_brain.py         # Brain rule-engine + parser tests
│   ├── test_eip712_signer.py # EIP-712 signing + nonce persistence
│   ├── test_exceptions.py    # Exception hierarchy tests
│   ├── test_metadata_handler.py   # Metadata generation & hashing
│   ├── test_nova_sonic_voice.py   # Voice command parser & fallback
│   ├── test_performance_tracker.py # Performance metrics tests
│   ├── test_risk_check.py    # Risk gate tests
│   ├── test_sign_trade.py    # Trade intent signing tests
│   └── test_validation_artifacts.py # Artifact data structure tests
├── .env.example              # Environment variable template (copy to .env)
├── .gitignore                # Git exclusions
├── LICENSE                   # MIT license
└── README.md                 # This file
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## 🏆 Hackathon

**Built for the Amazon Nova AI Hackathon on Devpost.**

Protocol Zero demonstrates how autonomous AI agents can operate transparently
on-chain using the ERC-8004 standard, with Amazon Nova providing
the cognitive backbone:

- **Nova Lite** — Agentic reasoning with tool-use (real Converse API)
- **Nova Voice** — Text intelligence + browser-side Web Speech API
- **Nova Act** — Browser-based contract auditing (simulated; SDK is invite-only)
- **Nova Embeddings** — Cosine-similarity scam detection (real embeddings when AWS available)

Every decision is cryptographically signed (EIP-712), risk-gated (6 independent checks),
and logged on-chain (Validation Registry) — creating a complete audit trail that
proves the agent's reasoning was sound *before* execution.

*Capital preservation first, profit second.* 🛡️
