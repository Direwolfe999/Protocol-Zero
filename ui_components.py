"""UI component helpers for Protocol Zero dashboard.

These helpers are intentionally presentation-only to keep refactors safe.
"""

from __future__ import annotations


def build_health_badges_html(checks: dict[str, tuple[str, str, int]]) -> str:
    """Return HTML for system health badges."""
    parts: list[str] = []
    for name, (icon, status, ms) in checks.items():
        color = "#64ffda" if status in ("LIVE", "READY", "SAFE") else "#ffd740" if status == "FALLBACK" else "#ff6b6b"
        ms_str = f" · {ms}ms" if ms > 0 else ""
        parts.append(
            f'<span style="display:inline-block;padding:0.2rem 0.6rem;margin:0.1rem 0.25rem;'
            f'border:1px solid {color}33;border-radius:6px;font-size:0.7rem;color:{color}">'
            f'{icon} {name}: <b>{status}</b>{ms_str}</span>'
        )
    return (
        '<div style="display:flex;flex-wrap:wrap;justify-content:center;margin:-0.3rem 0 0.5rem">'
        + "".join(parts)
        + "</div>"
    )


def footer_html() -> str:
    """Return static footer HTML."""
    return """
<div style="text-align:center;color:#3a3a5c;font-size:clamp(0.45rem,1.2vw,0.7rem);
            padding:0.5rem;word-break:break-word;line-height:1.6">
    Protocol Zero v1.0 &nbsp;·&nbsp; Autonomous Agent &nbsp;·&nbsp;
    ERC-8004 Compliant &nbsp;·&nbsp; EIP-712 Signed Intents &nbsp;·&nbsp;
    Nova Lite (Bedrock) &nbsp;·&nbsp; Nova Act &nbsp;·&nbsp;
    Nova Sonic &nbsp;·&nbsp; Nova Embeddings &nbsp;·&nbsp;
    On-Chain Trust &nbsp;·&nbsp;
    Validation Artifacts &nbsp;·&nbsp; Hackathon 2025/2026
</div>
"""
