from __future__ import annotations

import os

os.environ["PZ_SKIP_PAGE_CONFIG"] = "1"
os.environ["PZ_FORCE_ACTIVE_PANEL"] = "📈  P&L"

import dashboard  # noqa: E402,F401
