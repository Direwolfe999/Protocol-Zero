"""Session state persistence helpers for Protocol Zero dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def restore_persisted_state(session_state: Any, session_file: Path, persist_keys: list[str], logger: Any) -> None:
    """Restore persisted keys into `st.session_state`-like mapping."""
    if not session_file.exists():
        return
    try:
        raw = json.loads(session_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return
        for key in persist_keys:
            if key in raw:
                session_state[key] = raw[key]
    except Exception as exc:
        logger.debug("Session restore skipped: %s", exc)


def persist_state(session_state: Any, session_file: Path, persist_keys: list[str], logger: Any) -> None:
    """Persist selected keys from `st.session_state`-like mapping to disk."""
    try:
        session_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: session_state.get(k) for k in persist_keys}
        session_file.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    except Exception as exc:
        logger.debug("Session persist skipped: %s", exc)
