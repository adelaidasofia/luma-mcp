"""Thread-safe in-memory draft store with TTL.

Every Luma write tool returns a draft_id; nothing posts to Luma until
confirm_draft is called with that draft_id. Drafts expire after
LUMA_DRAFT_TTL seconds (default 3600 = 1h) and can only be confirmed once.

Mirror of whatsapp-mcp + slack-mcp draft pattern.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Draft:
    draft_id: str
    kind: str  # "create_event" | "create_ticket_type" | "create_coupon" | "send_email" | "update_event"
    payload: dict[str, Any]
    preview: str
    created_at: float
    expires_at: float
    confirmed: bool = False
    cancelled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class DraftStore:
    def __init__(self, ttl_seconds: int | None = None):
        self._lock = threading.Lock()
        self._items: dict[str, Draft] = {}
        self._ttl = ttl_seconds if ttl_seconds is not None else int(os.environ.get("LUMA_DRAFT_TTL", "3600"))

    def stage(self, kind: str, payload: dict[str, Any], preview: str, **extra: Any) -> Draft:
        draft_id = f"luma_{secrets.token_hex(8)}"
        now = time.time()
        d = Draft(
            draft_id=draft_id,
            kind=kind,
            payload=payload,
            preview=preview,
            created_at=now,
            expires_at=now + self._ttl,
            extra=dict(extra),
        )
        with self._lock:
            self._items[draft_id] = d
        return d

    def get(self, draft_id: str) -> Draft:
        with self._lock:
            d = self._items.get(draft_id)
        if d is None:
            raise ValueError(f"draft not found: {draft_id}")
        if d.cancelled:
            raise ValueError(f"draft cancelled: {draft_id}")
        if d.confirmed:
            raise ValueError(f"draft already confirmed: {draft_id}")
        if time.time() > d.expires_at:
            raise ValueError(f"draft expired: {draft_id}")
        return d

    def confirm(self, draft_id: str, executor: Callable[[Draft], dict[str, Any]]) -> dict[str, Any]:
        d = self.get(draft_id)
        result = executor(d)
        with self._lock:
            d.confirmed = True
        return result

    def cancel(self, draft_id: str) -> bool:
        with self._lock:
            d = self._items.get(draft_id)
            if d is None or d.confirmed or d.cancelled:
                return False
            d.cancelled = True
            return True

    def size(self) -> int:
        # Active (non-cancelled, non-confirmed, non-expired) drafts.
        now = time.time()
        with self._lock:
            return sum(1 for d in self._items.values() if not d.confirmed and not d.cancelled and d.expires_at > now)


# Module-level singleton — one draft store per process, shared across tools.
_store: DraftStore | None = None


def store() -> DraftStore:
    global _store
    if _store is None:
        _store = DraftStore()
    return _store
