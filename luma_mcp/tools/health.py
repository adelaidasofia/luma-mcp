"""Auth check + draft store size."""

from __future__ import annotations

from typing import Any

from luma_mcp import client, drafts
from luma_mcp.server import mcp


@mcp.tool()
def luma_health() -> dict[str, Any]:
    """Verify the LUMA_API_KEY is set and authenticates against the Luma API.

    Returns the calling user's profile on success (proves the key works) plus
    the active draft count so the operator can see if anything is staged.
    """
    try:
        me = client.health()
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "active_drafts": drafts.store().size(),
        }
    user = me.get("user", me) if isinstance(me, dict) else {}
    return {
        "ok": True,
        "user": {
            "name": user.get("name"),
            "email": user.get("email"),
            "api_id": user.get("api_id") or user.get("id"),
        },
        "active_drafts": drafts.store().size(),
    }


@mcp.tool()
def luma_cancel_draft(draft_id: str) -> dict[str, Any]:
    """Cancel an unconfirmed draft. Idempotent."""
    cancelled = drafts.store().cancel(draft_id)
    return {"draft_id": draft_id, "cancelled": cancelled}
