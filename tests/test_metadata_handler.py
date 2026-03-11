"""
Protocol Zero — Metadata Handler Unit Tests
=============================================
Tests the ERC-8004 metadata generation, hashing, and CID computation.
No AWS or blockchain required — pure data tests.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("RPC_URL", "http://localhost:8545")
os.environ.setdefault("PRIVATE_KEY", "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
os.environ.setdefault("CHAIN_ID", "31337")
os.environ.setdefault("IDENTITY_REGISTRY_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
os.environ.setdefault("REPUTATION_REGISTRY_ADDRESS", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")
os.environ.setdefault("VALIDATION_REGISTRY_ADDRESS", "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0")

from metadata_handler import (
    generate_metadata,
    compute_metadata_hash,
    save_metadata,
)


# ════════════════════════════════════════════════════════════
#  Metadata Generation
# ════════════════════════════════════════════════════════════

class TestGenerateMetadata:
    def test_returns_dict(self) -> None:
        meta = generate_metadata()
        assert isinstance(meta, dict)

    def test_has_agent_name(self) -> None:
        meta = generate_metadata(agent_name="TestBot")
        # Name should appear somewhere in the metadata
        meta_str = json.dumps(meta)
        assert "TestBot" in meta_str

    def test_has_version(self) -> None:
        meta = generate_metadata(version="2.0.0")
        meta_str = json.dumps(meta)
        assert "2.0.0" in meta_str

    def test_custom_capabilities(self) -> None:
        caps = ["SPOT_TRADING", "RISK_MANAGEMENT", "VOICE_CONTROL"]
        meta = generate_metadata(capabilities=caps)
        meta_str = json.dumps(meta)
        for cap in caps:
            assert cap in meta_str

    def test_has_registry_addresses(self) -> None:
        meta = generate_metadata()
        meta_str = json.dumps(meta)
        # Should contain registry references
        assert "0x" in meta_str


# ════════════════════════════════════════════════════════════
#  Hash Computation
# ════════════════════════════════════════════════════════════

class TestComputeHash:
    def test_hash_is_hex_string(self) -> None:
        meta = generate_metadata()
        h = compute_metadata_hash(meta)
        assert h.startswith("0x")
        assert len(h) == 66  # 0x + 64 hex chars

    def test_deterministic(self) -> None:
        meta = generate_metadata(agent_name="DeterministicBot", version="1.0.0")
        h1 = compute_metadata_hash(meta)
        h2 = compute_metadata_hash(meta)
        assert h1 == h2

    def test_different_metadata_different_hash(self) -> None:
        m1 = generate_metadata(agent_name="Bot1")
        m2 = generate_metadata(agent_name="Bot2")
        assert compute_metadata_hash(m1) != compute_metadata_hash(m2)


# ════════════════════════════════════════════════════════════
#  Save Metadata
# ════════════════════════════════════════════════════════════

class TestSaveMetadata:
    def test_saves_to_file(self, tmp_path: Path) -> None:
        output = tmp_path / "agent-identity.json"
        meta = generate_metadata()
        save_metadata(meta, output_path=output)
        assert output.exists()

        loaded = json.loads(output.read_text())
        assert isinstance(loaded, dict)

    def test_saved_json_is_valid(self, tmp_path: Path) -> None:
        output = tmp_path / "test-meta.json"
        meta = generate_metadata(agent_name="SaveTest")
        save_metadata(meta, output_path=output)

        loaded = json.loads(output.read_text())
        loaded_str = json.dumps(loaded)
        assert "SaveTest" in loaded_str
