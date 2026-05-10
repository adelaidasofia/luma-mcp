"""Append-only JSONL audit log of every API call + draft action.

Per-line shape: {ts, tool, action, args_redacted, status, latency_ms, error?}
Token redaction: any string starting with the Luma API key prefix is masked,
and any key containing 'api_key', 'token', 'cookie', 'secret' is redacted to
'[REDACTED]'.

Path: ~/.claude/luma-mcp/audit.log unless overridden via LUMA_AUDIT_LOG env.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_DEFAULT_PATH = Path.home() / ".claude" / "luma-mcp" / "audit.log"

_REDACTED_KEYS = {"api_key", "luma_api_key", "x_luma_api_key", "token", "cookie", "secret"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in _REDACTED_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str):
        # Heuristic: if it looks like a key (long, no spaces, has letters+digits), partial-redact.
        if len(value) >= 24 and " " not in value and any(c.isdigit() for c in value) and any(c.isalpha() for c in value):
            return f"{value[:4]}...{value[-4:]}"
        return value
    return value


def log(tool: str, action: str, args: dict[str, Any], status: str, latency_ms: float | None = None, error: str | None = None) -> None:
    path = Path(os.environ.get("LUMA_AUDIT_LOG", str(_DEFAULT_PATH)))
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "tool": tool,
        "action": action,
        "args": _redact(args),
        "status": status,
    }
    if latency_ms is not None:
        entry["latency_ms"] = round(latency_ms, 2)
    if error:
        entry["error"] = error[:500]  # cap error message length
    line = json.dumps(entry, ensure_ascii=False)
    with _LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
