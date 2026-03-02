"""
Protocol Zero — ERC-8004 Metadata Handler
===========================================
Generates and manages the `agent-identity.json` metadata file
required by the ERC-8004 Identity Registry standard.

ERC-8004 Identity Metadata Spec
────────────────────────────────
The Identity Registry mints an NFT for every autonomous agent.
The NFT's `tokenURI` points to a JSON document (usually on IPFS)
that describes the agent's identity, capabilities, and ownership.

Required fields:
    name             : Human-readable agent name
    description      : What the agent does
    version          : Semantic version of the agent software
    agent_address    : Checksummed EVM wallet address
    capabilities     : List of action strings the agent can perform
    registries       : Addresses of the three ERC-8004 registries
    metadata_hash    : Keccak-256 of the canonical JSON (for on-chain ref)

This module provides:
    1. `generate_metadata()`       — build the dict
    2. `save_metadata()`           — write to agent-identity.json
    3. `compute_metadata_hash()`   — keccak256 of the canonical JSON
    4. `compute_ipfs_cid_v1()`     — CIDv1 (raw / sha2-256) for IPFS pinning

Usage
-----
    from metadata_handler import generate_and_save

    meta = generate_and_save(
        agent_name="ProtocolZero",
        description="Trust-minimized DeFi trading agent",
        capabilities=["SPOT_TRADING", "RISK_MANAGEMENT"],
    )
    print(meta["metadata_hash"])   # 0x…
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import Web3

import config

logger = logging.getLogger("protocol_zero.metadata")

# Default output path (project root)
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "agent-identity.json"


# ════════════════════════════════════════════════════════════
#  1.  Generate the metadata dict
# ════════════════════════════════════════════════════════════

def generate_metadata(
    agent_name: str = "ProtocolZero",
    description: str = "Autonomous trust-minimized DeFi trading agent",
    version: str = "0.1.0",
    capabilities: list[str] | None = None,
    agent_wallet_address: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a fully compliant ERC-8004 agent identity metadata dict.

    Parameters
    ----------
    agent_name           : Human-readable name.
    description          : One-liner about the agent's purpose.
    version              : Semver string of the agent software.
    capabilities         : List of capability tags the agent supports.
    agent_wallet_address : Checksummed address.  If None, derived from
                           the PRIVATE_KEY in .env.
    extra_fields         : Any additional k/v pairs to merge in.

    Returns
    -------
    dict — the metadata document (without the hash; hash is added separately).
    """
    # Resolve agent address
    if agent_wallet_address is None:
        account = Account.from_key(config.PRIVATE_KEY)
        agent_wallet_address = account.address
    else:
        agent_wallet_address = Web3.to_checksum_address(agent_wallet_address)

    # Default capabilities
    if capabilities is None:
        capabilities = [
            "SPOT_TRADING",
            "RISK_MANAGEMENT",
            "MARKET_ANALYSIS",
            "EIP712_SIGNING",
        ]

    metadata: dict[str, Any] = {
        # ── Core identity (ERC-8004 required) ─────────────
        "name":            agent_name,
        "description":     description,
        "version":         version,
        "agent_address":   agent_wallet_address,

        # ── Capabilities ──────────────────────────────────
        "capabilities":    capabilities,

        # ── ERC-8004 registry references ──────────────────
        "registries": {
            "identity":    Web3.to_checksum_address(config.IDENTITY_REGISTRY_ADDRESS),
            "reputation":  Web3.to_checksum_address(config.REPUTATION_REGISTRY_ADDRESS),
            "validation":  Web3.to_checksum_address(config.VALIDATION_REGISTRY_ADDRESS),
        },

        # ── Chain info ────────────────────────────────────
        "chain_id":        config.CHAIN_ID,

        # ── Timestamps ────────────────────────────────────
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "schema_version":  "ERC-8004-v1",
    }

    # Merge any extra fields the caller provides
    if extra_fields:
        metadata.update(extra_fields)

    logger.info("📝  Generated metadata for agent '%s' (%s)", agent_name, agent_wallet_address)
    return metadata


# ════════════════════════════════════════════════════════════
#  2.  Canonical JSON serialization
# ════════════════════════════════════════════════════════════

def to_canonical_json(metadata: dict[str, Any]) -> str:
    """
    Serialize metadata to a *canonical* JSON string.

    Canonical means:
      - Keys are sorted alphabetically (deterministic ordering).
      - No trailing whitespace.
      - UTF-8 encoded.

    This ensures the same metadata always produces the same hash,
    regardless of Python dict insertion order.
    """
    return json.dumps(metadata, sort_keys=True, indent=2, ensure_ascii=False)


# ════════════════════════════════════════════════════════════
#  3.  Compute Keccak-256 hash (for on-chain reference)
# ════════════════════════════════════════════════════════════

def compute_metadata_hash(metadata: dict[str, Any]) -> str:
    """
    Keccak-256 hash of the canonical JSON representation.

    This hash can be stored on-chain in the Identity Registry so
    anyone can verify the metadata file hasn't been tampered with.

    Returns
    -------
    str — "0x"-prefixed 64-char hex hash.
    """
    canonical = to_canonical_json(metadata)
    raw_hash = Web3.keccak(text=canonical)
    hex_hash = "0x" + raw_hash.hex()
    logger.debug("Metadata keccak256: %s", hex_hash)
    return hex_hash


# ════════════════════════════════════════════════════════════
#  4.  Compute IPFS-compatible content hash (CIDv1 / sha2-256)
# ════════════════════════════════════════════════════════════

def compute_ipfs_cid_v1(metadata: dict[str, Any]) -> str:
    """
    Compute a sha2-256 digest of the canonical JSON.

    This is the raw content hash that IPFS uses under the hood.
    When you `ipfs add` the file, the resulting CID wraps this digest.

    For a full CIDv1 you'd also need the multicodec prefix, but
    for pinning services (Pinata, web3.storage) the sha256 hex
    is sufficient to verify integrity after upload.

    Returns
    -------
    str — "sha256:<hex>" formatted content hash.
    """
    canonical = to_canonical_json(metadata)
    sha256_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    content_hash = f"sha256:{sha256_digest}"
    logger.debug("IPFS content hash: %s", content_hash)
    return content_hash


# ════════════════════════════════════════════════════════════
#  5.  Save to disk
# ════════════════════════════════════════════════════════════

def save_metadata(
    metadata: dict[str, Any],
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Write the metadata dict to a JSON file.

    The `metadata_hash` and `ipfs_content_hash` fields are injected
    automatically before writing.

    Returns
    -------
    Path — absolute path to the written file.
    """
    output_path = Path(output_path)

    # Inject hashes computed over the metadata WITHOUT the hash fields
    metadata_copy = {k: v for k, v in metadata.items()
                     if k not in ("metadata_hash", "ipfs_content_hash")}

    metadata["metadata_hash"]     = compute_metadata_hash(metadata_copy)
    metadata["ipfs_content_hash"] = compute_ipfs_cid_v1(metadata_copy)

    canonical = to_canonical_json(metadata)
    output_path.write_text(canonical, encoding="utf-8")

    logger.info("💾  Saved agent-identity.json → %s", output_path)
    logger.info("    keccak256      : %s", metadata["metadata_hash"])
    logger.info("    IPFS sha256    : %s", metadata["ipfs_content_hash"])
    return output_path


# ════════════════════════════════════════════════════════════
#  6.  All-in-one convenience
# ════════════════════════════════════════════════════════════

def generate_and_save(
    agent_name: str = "ProtocolZero",
    description: str = "Autonomous trust-minimized DeFi trading agent",
    capabilities: list[str] | None = None,
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Generate metadata, compute hashes, write to disk, return the dict.
    """
    metadata = generate_metadata(
        agent_name=agent_name,
        description=description,
        capabilities=capabilities,
        **kwargs,
    )
    save_metadata(metadata, output_path)
    return metadata


# ════════════════════════════════════════════════════════════
#  7.  Verify an existing file against its embedded hash
# ════════════════════════════════════════════════════════════

def verify_metadata_file(file_path: Path | str = DEFAULT_OUTPUT_PATH) -> bool:
    """
    Read an agent-identity.json and verify its `metadata_hash` is correct.

    Returns True if the hash matches, False otherwise.
    """
    file_path = Path(file_path)
    data = json.loads(file_path.read_text(encoding="utf-8"))

    stored_hash = data.pop("metadata_hash", None)
    data.pop("ipfs_content_hash", None)

    computed = compute_metadata_hash(data)

    if stored_hash == computed:
        logger.info("✅  Metadata hash verified: %s", computed)
        return True
    else:
        logger.warning(
            "❌  Hash mismatch!\n    Stored  : %s\n    Computed: %s",
            stored_hash, computed,
        )
        return False


# ════════════════════════════════════════════════════════════
#  CLI Smoke Test
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("─" * 60)
    print("  Protocol Zero — Metadata Handler Smoke Test")
    print("─" * 60)

    meta = generate_and_save(
        agent_name="ProtocolZero",
        description="Trust-minimized autonomous DeFi trading agent for hackathon",
        capabilities=["SPOT_TRADING", "RISK_MANAGEMENT", "MARKET_ANALYSIS", "EIP712_SIGNING"],
    )

    print(f"\n  Agent        : {meta['name']}")
    print(f"  Address      : {meta['agent_address']}")
    print(f"  Capabilities : {', '.join(meta['capabilities'])}")
    print(f"  Keccak-256   : {meta['metadata_hash']}")
    print(f"  IPFS Hash    : {meta['ipfs_content_hash']}")
    print(f"  File         : {DEFAULT_OUTPUT_PATH}")

    # Verify round-trip
    ok = verify_metadata_file()
    print(f"\n  Verification : {'✅ PASSED' if ok else '❌ FAILED'}")
