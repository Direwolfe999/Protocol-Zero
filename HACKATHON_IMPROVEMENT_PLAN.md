# 🏆 Protocol Zero — Hackathon Improvement Master Plan

## Complete Gap Analysis & Action Items to Win the Amazon Nova AI Trading Agents Hackathon

> **Date**: March 4, 2026  
> **Project**: Protocol Zero — Autonomous Trust-Minimized DeFi Trading Agent  
> **Hackathon**: AI Trading Agents × ERC-8004 (Amazon Nova on LabLab.ai)

---

## 📊 CURRENT STATE ASSESSMENT

### What You Already Have (Strengths)
Your project has a solid foundation. Here's what's working:

| Component | File | Status |
|-----------|------|--------|
| AI Brain (Amazon Nova via Bedrock) | `brain.py` | ✅ Working — fetches OHLCV data, calls Nova Lite, returns JSON decisions |
| EIP-712 Trade Intent Signing | `eip712_signer.py` | ✅ Working — nonce, expiry, proper typed data |
| Chain Interaction (3 Registries) | `chain_interactor.py` | ✅ Skeleton — Identity, Reputation, Validation registry calls |
| Risk Checks (6 checks) | `risk_check.py` | ✅ Working — position size, daily loss, frequency, concentration, confidence, expiry |
| Trade Validator & Signer | `sign_trade.py` | ✅ Working — validate → sign → broadcast pipeline |
| Agent Metadata (ERC-8004) | `metadata_handler.py` | ✅ Working — generates `agent-identity.json`, keccak256 hash, IPFS hash |
| Cinematic Dashboard | `dashboard.py` | ✅ Impressive UI — cognitive stream, regime orb, risk heatmap, kill switch |
| Main Loop Orchestrator | `main.py` | ✅ Working — fetch → brain → risk gate → sign → submit → reputation |
| Configuration | `config.py` | ✅ Clean — centralized env loading |

### Your Score So Far (Estimated)
Based on the hackathon judging criteria:
- **Identity Registration**: 6/10 — You register but don't follow the ERC-8004 spec properly
- **Reputation from Outcomes**: 4/10 — You log PnL but not in the correct ERC-8004 format
- **Validation Artifacts**: 3/10 — EIP-712 signing exists but Validation Registry usage is wrong
- **Capital Sandbox Integration**: 2/10 — No Hackathon Capital Vault / Risk Router integration
- **Dashboard & Presentation**: 8/10 — Excellent UI, very impressive

**Estimated Overall: ~45/100** — Good base, but critical spec compliance gaps.

---

## 🚨 CRITICAL ISSUES (Must Fix to Not Get Disqualified)

### CRITICAL #1: Your ERC-8004 Registry ABIs Don't Match the Actual Spec

**Problem**: Your `chain_interactor.py` uses **invented ABI stubs** that do NOT match the actual ERC-8004 specification at all. The hackathon judges will deploy real ERC-8004 contracts, and your agent won't be able to talk to them.

**What Your Code Has vs. What ERC-8004 Actually Specifies**:

#### Identity Registry — Your ABI is WRONG

```
YOUR CODE (WRONG):
  registerAgent(string handle) → uint256 tokenId
  isRegistered(address agent) → bool
  getTokenId(address agent) → uint256

ACTUAL ERC-8004 SPEC:
  register(string agentURI) → uint256 agentId
  register(string agentURI, MetadataEntry[] metadata) → uint256 agentId
  register() → uint256 agentId              // agentURI added later
  setAgentURI(uint256 agentId, string newURI)
  setMetadata(uint256 agentId, string key, bytes value)
  getMetadata(uint256 agentId, string key) → bytes
  setAgentWallet(uint256 agentId, address newWallet, uint256 deadline, bytes signature)
  getAgentWallet(uint256 agentId) → address
```

**FIX**: Rewrite your `IDENTITY_REGISTRY_ABI` in `chain_interactor.py` to use the actual functions:
- `register(string agentURI)` instead of `registerAgent(string handle)`
- Generate a proper **Agent Registration JSON file** (not just a handle string) and host it (IPFS or data: URI)
- The registration JSON MUST follow this exact schema:
```json
{
  "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
  "name": "ProtocolZero",
  "description": "Autonomous trust-minimized DeFi trading agent",
  "image": "https://...",
  "services": [
    {"name": "web", "endpoint": "https://your-dashboard-url/"},
    {"name": "MCP", "endpoint": "https://...", "version": "2025-06-18"}
  ],
  "x402Support": false,
  "active": true,
  "registrations": [
    {
      "agentId": 1,
      "agentRegistry": "eip155:11155111:0xYourIdentityRegistryAddress"
    }
  ],
  "supportedTrust": ["reputation"]
}
```

#### Reputation Registry — Your ABI is WRONG

```
YOUR CODE (WRONG):
  logAction(address agent, string actionType, int256 pnlBps, string metadata)
  getReputation(address agent) → (uint256, int256)

ACTUAL ERC-8004 SPEC:
  giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
               string tag1, string tag2, string endpoint,
               string feedbackURI, bytes32 feedbackHash)
  readFeedback(uint256 agentId, address clientAddress, uint64 feedbackIndex) 
               → (int128 value, uint8 valueDecimals, string tag1, string tag2, bool isRevoked)
  getSummary(uint256 agentId, address[] clientAddresses, string tag1, string tag2)
               → (uint64 count, int128 summaryValue, uint8 summaryValueDecimals)
  getClients(uint256 agentId) → address[]
```

**FIX**: 
- Replace `logAction()` with `giveFeedback()` 
- Use `agentId` (the NFT token ID) instead of raw address
- Use proper `tag1` values like `"tradingYield"`, `"successRate"`, etc.
- Use `tag2` for time period: `"day"`, `"week"`, `"month"`
- The `value` + `valueDecimals` system: e.g., PnL of -3.2% → value=-32, valueDecimals=1

#### Validation Registry — Your ABI is WRONG

```
YOUR CODE (WRONG):
  submitIntent(bytes signature, bytes32 intentHash) → bool valid

ACTUAL ERC-8004 SPEC:
  validationRequest(address validatorAddress, uint256 agentId,
                    string requestURI, bytes32 requestHash)
  validationResponse(bytes32 requestHash, uint8 response,
                     string responseURI, bytes32 responseHash, string tag)
  getValidationStatus(bytes32 requestHash) 
                     → (address, uint256, uint8, bytes32, string, uint256)
  getSummary(uint256 agentId, address[] validatorAddresses, string tag)
                     → (uint64 count, uint8 averageResponse)
```

**FIX**:
- The Validation Registry is NOT a "Risk Router that validates signatures"
- It's a registry where the agent REQUESTS validation and validators RESPOND
- Your agent should: (1) execute a trade, (2) post a `validationRequest` with a URI pointing to the trade details, (3) a validator contract/service responds with a score 0-100
- The `requestHash` is `keccak256` of the request payload, NOT the EIP-712 hash

---

### CRITICAL #2: No Hackathon Capital Sandbox Integration

**Problem**: The hackathon provides a **Hackathon Capital Vault** and **Risk Router contract**. Your agent MUST use these to execute trades. You're currently doing direct DEX interaction which won't count for the leaderboard.

**What You Need to Add**:
1. **Claim sandbox capital** — call the vault contract to get your sub-account funded
2. **Submit TradeIntents to the Risk Router** — the hackathon's Risk Router enforces:
   - Max position size
   - Max leverage
   - Whitelisted markets only
   - Daily loss limit
3. **All PnL is measured through the vault** — this feeds the leaderboard

**FIX**: Add a `RISK_ROUTER_ADDRESS` and `CAPITAL_VAULT_ADDRESS` to your `.env` and `config.py`. Create functions to:
- `claim_sandbox_capital()` → call the vault to get funded
- `submit_to_risk_router(signed_intent)` → submit through the hackathon's router, NOT directly to DEX

---

### CRITICAL #3: Agent Registration JSON Doesn't Follow the Spec

**Problem**: Your `metadata_handler.py` generates a custom JSON that doesn't follow the ERC-8004 registration file structure at all.

**Your current JSON schema** (WRONG):
```json
{
  "name": "ProtocolZero",
  "description": "...",
  "version": "0.1.0",
  "agent_address": "0x...",
  "capabilities": ["SPOT_TRADING", ...],
  "registries": {"identity": "0x...", ...},
  "chain_id": 11155111,
  "schema_version": "ERC-8004-v1"
}
```

**The REQUIRED schema** (per ERC-8004 spec):
```json
{
  "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
  "name": "ProtocolZero",
  "description": "Autonomous trust-minimized DeFi trading agent...",
  "image": "https://your-image-url.png",
  "services": [
    {"name": "web", "endpoint": "https://your-dashboard-url/"}
  ],
  "x402Support": false,
  "active": true,
  "registrations": [
    {
      "agentId": 1,
      "agentRegistry": "eip155:CHAIN_ID:IDENTITY_REGISTRY_ADDRESS"
    }
  ],
  "supportedTrust": ["reputation"]
}
```

**FIX**: Rewrite `metadata_handler.py` → `generate_metadata()` to produce the correct schema. Add the `type` field, `services` array, `registrations` array with `agentRegistry` in the `eip155:chainId:address` format.

---

## ⚠️ HIGH-PRIORITY IMPROVEMENTS (Will Significantly Boost Your Score)

### IMPROVEMENT #1: Proper Validation Artifacts Pipeline

**What Judges Want**: Every significant action (trade, risk check, strategy checkpoint) must produce a **validation artifact** that can be independently verified.

**What to Add**:
1. After every trade decision, create a JSON artifact containing:
   - The market data snapshot that was used
   - The AI's reasoning (raw LLM output)
   - The risk check results
   - The signed EIP-712 intent
   - A timestamp
2. Hash this artifact (`keccak256`)
3. Upload to IPFS (or use a `data:` URI for the hackathon)
4. Call `validationRequest()` on the Validation Registry with:
   - `requestURI` = IPFS/data URI of the artifact
   - `requestHash` = keccak256 of the artifact JSON

**New function to add to `chain_interactor.py`**:
```python
def submit_validation_request(self, artifact_json: str, validator_address: str) -> str:
    """Submit a validation request for a trade artifact."""
    artifact_hash = Web3.keccak(text=artifact_json)
    # For hackathon, use data URI instead of IPFS
    import base64
    data_uri = "data:application/json;base64," + base64.b64encode(
        artifact_json.encode()).decode()
    fn = self.validation.functions.validationRequest(
        Web3.to_checksum_address(validator_address),
        self.get_token_id(),  # agentId
        data_uri,
        artifact_hash,
    )
    return self._send_tx(fn)
```

### IMPROVEMENT #2: Proper Reputation Feedback with Correct Schema

**What to Add**: After each trading session or at regular intervals, log measurable outcomes using the correct `giveFeedback()` format:

```python
def log_trading_yield(self, agent_id: int, yield_bps: int, period: str = "day"):
    """Log trading yield as ERC-8004 reputation feedback."""
    fn = self.reputation.functions.giveFeedback(
        agent_id,           # uint256 agentId
        yield_bps,          # int128 value (e.g., -32 for -3.2%)
        1,                  # uint8 valueDecimals (1 decimal place)
        "tradingYield",     # string tag1
        period,             # string tag2 ("day", "week", "month")
        "",                 # string endpoint (optional)
        "",                 # string feedbackURI (optional)
        b'\x00' * 32,       # bytes32 feedbackHash (optional)
    )
    return self._send_tx(fn)
```

Use these standard tags from the spec:
- `tag1="tradingYield"`, `tag2="day"` → daily PnL
- `tag1="successRate"` → win rate percentage
- `tag1="responseTime"` → how fast the agent reacts

### IMPROVEMENT #3: Sharpe Ratio & Drawdown Tracking

**Why**: The leaderboard scores on **PnL, Sharpe ratio, max drawdown, and validation score**. You currently don't track Sharpe or drawdown.

**What to Add in `risk_check.py`** or a new section in `main.py`:

```python
import numpy as np

class PerformanceTracker:
    """Track metrics the leaderboard cares about."""
    
    def __init__(self):
        self.returns: list[float] = []  # list of period returns
        self.equity_curve: list[float] = [10000.0]  # starting capital
        self.peak_equity: float = 10000.0
        self.max_drawdown: float = 0.0
    
    def record_return(self, pnl_usd: float):
        last_equity = self.equity_curve[-1]
        new_equity = last_equity + pnl_usd
        self.equity_curve.append(new_equity)
        self.returns.append(pnl_usd / last_equity if last_equity > 0 else 0)
        
        # Track max drawdown
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity
        drawdown = (self.peak_equity - new_equity) / self.peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    @property
    def sharpe_ratio(self) -> float:
        if len(self.returns) < 2:
            return 0.0
        mean_return = np.mean(self.returns)
        std_return = np.std(self.returns, ddof=1)
        if std_return == 0:
            return 0.0
        # Annualized (assuming hourly returns, ~8760 hours/year)
        return (mean_return / std_return) * np.sqrt(8760)
    
    @property
    def total_pnl_pct(self) -> float:
        return ((self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0]) * 100
```

### IMPROVEMENT #4: Brain Prompt Needs Risk Parameters

**Problem**: Your brain prompt doesn't include stop-loss, take-profit, risk score, market regime, or position size percentage — but `sign_trade.py` REQUIRES all of these fields for validation. The two modules are disconnected.

**FIX**: Update the system prompt in `brain.py` to require these additional fields:

```python
_SYSTEM_PROMPT = """\
You are Protocol Zero — an autonomous DeFi trading agent.
Your mandate is capital preservation first, profit second.

You MUST reply with a single JSON object. No markdown, no explanation outside the JSON.

Schema:
{
  "action":               "BUY" | "SELL" | "HOLD",
  "asset":                "<TICKER>",
  "amount_usd":           <float>,
  "reason":               "<one sentence>",
  "confidence":           <float 0.0-1.0>,
  "risk_score":           <int 1-10>,
  "position_size_percent": <float 0.0-2.0>,
  "stop_loss_percent":     <float>,
  "take_profit_percent":   <float>,
  "market_regime":         "TRENDING" | "RANGING" | "VOLATILE" | "UNCERTAIN"
}

Rules:
- Never exceed the max trade size provided.
- If uncertain, choose HOLD.
- Always set stop-loss (max 10%) and take-profit.
- risk_score 1 = very low risk, 10 = maximum risk.
- position_size_percent MUST be ≤ 2.0%.
- Base decisions on price momentum, RSI, SMA crossovers, and volume.
"""
```

### IMPROVEMENT #5: Connect sign_trade.py into the Main Loop

**Problem**: `sign_trade.py` has excellent validation logic (8 checks including stop-loss, take-profit, risk score, market regime) but **it's never called by `main.py`**. The main loop uses `chain_interactor.submit_intent()` directly, bypassing all of `sign_trade.py`'s validation.

**FIX in `main.py`**:
```python
from sign_trade import validate_and_sign

# In the tick() function, after risk gate passes:
result = validate_and_sign(decision, broadcast=True)
if result["status"] == "rejected":
    logger.warning("⛔ Trade REJECTED by sign_trade validator: %s", result["validation"]["errors"])
    return decision
```

---

## 📈 MEDIUM-PRIORITY IMPROVEMENTS (Differentiation & Polish)

### IMPROVEMENT #6: Add EIP-155 Chain-ID Binding

**Requirement**: The hackathon explicitly lists "EIP-155 chain-id binding" as required technology. Your EIP-712 domain already includes `chainId`, which is good. BUT you should also ensure all transactions use EIP-155 replay protection.

**What to Verify**: In `chain_interactor.py` → `_send_tx()`, you already include `chainId` in the transaction dict. ✅ This is correct. Just document it clearly.

### IMPROVEMENT #7: Add EIP-1271 Smart Contract Wallet Support

**Requirement**: "EIP-1271 support for smart-contract wallets" is listed as required.

**What to Add**: Add a check in your signature verification that tries EIP-1271 `isValidSignature()` if `ecrecover` fails:

```python
EIP1271_ABI = [{
    "inputs": [
        {"name": "hash", "type": "bytes32"},
        {"name": "signature", "type": "bytes"}
    ],
    "name": "isValidSignature",
    "outputs": [{"name": "", "type": "bytes4"}],
    "stateMutability": "view",
    "type": "function",
}]

# Magic value returned by EIP-1271 on success
EIP1271_MAGIC = bytes.fromhex("1626ba7e")
```

### IMPROVEMENT #8: Deploy Your Own ERC-8004 Contracts on Sepolia

**Why**: If the hackathon hasn't provided contract addresses yet, you need to deploy your own for testing. Even if they do provide them, having your own shows initiative.

**What to Do**:
1. Write minimal Solidity contracts for the 3 registries (Identity, Reputation, Validation)
2. Deploy to Sepolia using Foundry/Hardhat
3. Update your `.env` with the deployed addresses
4. Add a `contracts/` directory with the Solidity source

The ERC-8004 spec article gives you exact Solidity examples. Use them.

### IMPROVEMENT #9: Add Multi-Asset Support

**Current State**: You only trade `BTC/USDT`. The hackathon mentions "whitelisted markets" (plural).

**FIX**: 
- Update `brain.py` to accept a list of pairs and analyze the best opportunity
- Add `TRADING_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT` to config
- The brain should pick the best risk/reward across all pairs

### IMPROVEMENT #10: On-Chain Event Emission for Leaderboard

**Requirement**: "Every trade and checkpoint emits events. Validators post a validation score."

**What to Add**: Make sure your contracts emit events that the leaderboard indexer can pick up:
- `TradeExecuted(uint256 indexed agentId, string action, string asset, uint256 amountUsd, uint256 timestamp)`
- `RiskCheckPassed(uint256 indexed agentId, bytes32 intentHash, uint256 timestamp)`
- `StrategyCheckpoint(uint256 indexed agentId, int256 pnlBps, uint256 sharpeRatio, uint256 maxDrawdown)`

---

## 🌟 BONUS FEATURES (Will Make You Stand Out)

### BONUS #1: TEE-Backed Attestations (Optional but HIGH Impact)

**Why**: The spec lists "TEE-backed attestations or verifiable execution proofs" as bonus technology for trust tiering. This is a MAJOR differentiator.

**Simplified Version for Hackathon**:
- You don't need actual Oasis ROFL
- Instead, create a **self-attestation** system:
  1. Hash the brain's input (market data) + output (decision) + code version
  2. Sign the hash with a separate "attestation key"
  3. Post it to the Validation Registry
  4. In your presentation, explain this would be replaced with TEE in production

### BONUS #2: Off-Chain Subgraph / Indexer

**Why**: "Off-chain indexers/subgraphs for discovery dashboards" is listed as bonus.

**Simplified Version**:
- Add a function that reads events from the chain and displays them in the dashboard
- Show a "Trust Explorer" tab that queries:
  - Agent identity (from Identity Registry)
  - Cumulative reputation score (from Reputation Registry)
  - Validation history (from Validation Registry)

### BONUS #3: Circuit Breaker with On-Chain Enforcement

**Current State**: Your kill switch is dashboard-only (frontend). It doesn't enforce anything on-chain.

**Improvement**:
- Add a `CircuitBreaker` contract that the Risk Router checks before executing trades
- If daily loss limit is hit, the circuit breaker blocks ALL further trades on-chain
- Your agent calls `triggerCircuitBreaker()` when the kill switch is activated

### BONUS #4: Strategy Checkpoints

**Why**: The hackathon specifically asks for "strategy checkpoints" as validation artifacts.

**What to Add**: Every N trades (e.g., every 10), emit a strategy checkpoint:
```python
def emit_strategy_checkpoint(self):
    checkpoint = {
        "agentId": self.get_token_id(),
        "timestamp": int(time.time()),
        "total_trades": self.performance.trade_count,
        "cumulative_pnl_bps": int(self.performance.total_pnl_pct * 100),
        "sharpe_ratio": round(self.performance.sharpe_ratio, 4),
        "max_drawdown_bps": int(self.performance.max_drawdown * 10000),
        "current_positions": dict(self.risk_state.positions),
    }
    # Hash and submit to Validation Registry
    self.submit_validation_request(
        json.dumps(checkpoint),
        validator_address=config.VALIDATOR_ADDRESS,
    )
```

---

## 🔧 CODE-LEVEL FIXES (Quick Wins)

### FIX #1: `sign_trade.py` Has Different ENV Var Names
- Uses `AGENT_PRIVATE_KEY` instead of `PRIVATE_KEY`
- Uses `VALIDATION_REGISTRY_ADDR` instead of `VALIDATION_REGISTRY_ADDRESS`
- Uses `TARGET_CHAIN` which doesn't exist in config.py
- **FIX**: Standardize to use `config.py` imports instead of direct `os.getenv()`

### FIX #2: `eip712_signer.py` and `chain_interactor.py` Duplicate Signing Logic
- Both files implement EIP-712 signing independently
- `chain_interactor.py` has a simpler version (no nonce, no expiry)
- `eip712_signer.py` has the proper version (with nonce + expiry)
- **FIX**: Remove the signing logic from `chain_interactor.py` and import from `eip712_signer.py`

### FIX #3: `risk_check.py` and `main.py` Have Duplicate Risk Gate Logic
- `main.py` has a `RiskGate` class with 3 checks
- `risk_check.py` has a `RiskState` + 6 check functions
- **FIX**: Remove the `RiskGate` class from `main.py` and use `risk_check.run_all_checks()` instead

### FIX #4: Dashboard Uses Mock/Simulated Data
- The dashboard generates fake data instead of connecting to real agent state
- **FIX**: Connect dashboard to the actual agent's state (read from a shared state file, database, or Redis)

### FIX #5: Missing `numpy` in `requirements.txt`
- `dashboard.py` imports `numpy` but it's not in requirements.txt
- **FIX**: Add `numpy>=1.26.0` to `requirements.txt`

---

## 📋 IMPLEMENTATION PRIORITY ORDER

Here's the exact order you should implement changes for maximum impact:

### Phase 1: Spec Compliance (DO THIS FIRST — 4-6 hours)
1. ✏️ Rewrite `IDENTITY_REGISTRY_ABI` in `chain_interactor.py` to match ERC-8004 spec
2. ✏️ Rewrite `REPUTATION_REGISTRY_ABI` to use `giveFeedback()` instead of `logAction()`
3. ✏️ Rewrite `VALIDATION_REGISTRY_ABI` to use `validationRequest()`/`validationResponse()`
4. ✏️ Rewrite `metadata_handler.py` to produce compliant Agent Registration JSON
5. ✏️ Update `chain_interactor.py` registration flow to use `register(agentURI)`
6. ✏️ Add `RISK_ROUTER_ADDRESS` and `CAPITAL_VAULT_ADDRESS` to config

### Phase 2: Integration Fixes (3-4 hours)
7. ✏️ Update brain.py system prompt to include all required fields
8. ✏️ Integrate `sign_trade.py` validation into `main.py` loop
9. ✏️ Remove duplicate code (RiskGate in main.py, duplicate signing)
10. ✏️ Standardize env vars in `sign_trade.py` to use `config.py`

### Phase 3: Scoring Features (3-4 hours)
11. ✏️ Add `PerformanceTracker` (Sharpe ratio, max drawdown)
12. ✏️ Add validation artifacts pipeline (hash + submit to Validation Registry)
13. ✏️ Add strategy checkpoint emission
14. ✏️ Add proper reputation logging with correct tags

### Phase 4: Polish & Bonus (2-3 hours)
15. ✏️ Connect dashboard to real agent state
16. ✏️ Add multi-asset analysis capability
17. ✏️ Add self-attestation system
18. ✏️ Deploy contracts to Sepolia (if hackathon doesn't provide them)

### Phase 5: Presentation Prep (1-2 hours)
19. ✏️ Add a `README.md` with architecture diagram
20. ✏️ Record a demo video showing the full flow
21. ✏️ Prepare slides explaining trust-minimization approach

---

## 🏗️ NEW FILES / DIRECTORIES TO ADD

```
Protocol Zero/
├── contracts/                          # NEW — Solidity contracts
│   ├── IdentityRegistry.sol            # ERC-8004 compliant
│   ├── ReputationRegistry.sol          # ERC-8004 compliant
│   ├── ValidationRegistry.sol          # ERC-8004 compliant
│   └── deploy.js                       # Deployment script
├── agent-registration.json             # NEW — ERC-8004 compliant metadata
├── performance_tracker.py              # NEW — Sharpe, drawdown, PnL
├── validation_artifacts.py             # NEW — Create & submit validation artifacts
├── README.md                           # NEW — Project documentation
├── brain.py                            # MODIFY — Updated prompt
├── chain_interactor.py                 # MODIFY — Correct ABIs
├── config.py                           # MODIFY — Add vault/router addresses
├── main.py                             # MODIFY — Integrate sign_trade + risk_check properly
├── metadata_handler.py                 # MODIFY — ERC-8004 compliant JSON
├── sign_trade.py                       # MODIFY — Use config.py
├── requirements.txt                    # MODIFY — Add numpy
└── dashboard.py                        # MODIFY — Connect to real state
```

---

## 🎯 JUDGING CRITERIA ALIGNMENT

| Criteria | Weight | Your Current | After Fixes | How |
|----------|--------|-------------|-------------|-----|
| Agent registers identity on ERC-8004 | HIGH | ❌ Wrong ABI | ✅ Proper register(agentURI) + compliant JSON | Phase 1 |
| Accumulates measurable reputation | HIGH | ❌ Wrong ABI | ✅ giveFeedback() with proper tags | Phase 1 |
| Produces validation artifacts | HIGH | ❌ Wrong ABI | ✅ validationRequest() + artifact hashing | Phase 1+3 |
| Operates through Capital Sandbox | HIGH | ❌ Not integrated | ⚠️ Ready (needs hackathon addresses) | Phase 1 |
| PnL performance | MEDIUM | ⚠️ Basic | ✅ Multi-asset, better prompts | Phase 2+3 |
| Sharpe ratio | MEDIUM | ❌ Not tracked | ✅ PerformanceTracker | Phase 3 |
| Max drawdown | MEDIUM | ❌ Not tracked | ✅ PerformanceTracker | Phase 3 |
| Validation score | MEDIUM | ❌ None | ✅ Self-attestation pipeline | Phase 3+4 |
| Dashboard & presentation | LOW-MED | ✅ Excellent | ✅ Even better with real data | Phase 4 |

---

## 💡 KEY INSIGHT FOR WINNING

The hackathon is NOT primarily about trading performance. It's about **demonstrating trust-minimized behavior**. Focus on:

1. **Every action is verifiable** — signed intents, hashed artifacts, on-chain records
2. **Every decision is explainable** — the brain's reasoning is logged and can be audited
3. **Risk is enforced at multiple layers** — AI level, code level, on-chain level
4. **Performance is measurable** — PnL, Sharpe, drawdown, all tracked and logged on-chain
5. **Identity is portable** — ERC-721 NFT with compliant registration JSON

Your dashboard is already a huge asset for presentation. But the underlying on-chain compliance with ERC-8004 is what the judges will really look at. Fix that first, and the fancy UI becomes the cherry on top instead of lipstick on a pig.

---

## 🔗 REFERENCE: Key ERC-8004 Spec Differences

| Concept | Your Implementation | ERC-8004 Spec | Action |
|---------|-------------------|---------------|--------|
| Agent ID | Wallet address | ERC-721 tokenId (`agentId`) | Use tokenId everywhere |
| Registration | `registerAgent(handle)` | `register(agentURI)` | Rewrite ABI + function |
| Registration metadata | Custom JSON | `registration-v1` schema with services, registrations, supportedTrust | Rewrite metadata_handler.py |
| Reputation signal | `logAction(address, string, int256, string)` | `giveFeedback(uint256, int128, uint8, string, string, string, string, bytes32)` | Rewrite ABI + function |
| Reputation value | PnL in basis points (int256) | Signed fixed-point `value` + `valueDecimals` (int128 + uint8) | Convert your PnL to value/decimals format |
| Reputation tags | None | `tag1` (metric type) + `tag2` (period/detail) | Add tag system |
| Validation | Submit signature for verification | Request validation → validator responds with 0-100 score | Complete rewrite of validation flow |
| On-chain metadata | Not used | `setMetadata(agentId, key, bytes)` / `getMetadata(agentId, key)` | Add metadata storage calls |
| Agent wallet | Implicit (signing key) | Explicit `setAgentWallet()` with EIP-712 proof | Add agentWallet setup |

---

**Good luck! 🚀 You've got a strong foundation — now make it spec-compliant and you'll be in serious contention.**
