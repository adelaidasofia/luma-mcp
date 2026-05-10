"""Guest list reads. RSVPs, registrations, attendance."""

from __future__ import annotations

from typing import Any

from luma_mcp import client
from luma_mcp._shared import LumaGuest
from luma_mcp.server import mcp


@mcp.tool()
def luma_list_event_guests(
    event_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List RSVPs / guests for an event.

    Args:
        event_id: Luma event api_id.
        status: Filter by status (e.g. "going", "declined", "waitlist", "approved").
                None = all statuses.
        limit: Max results per call. Luma caps at 200.

    Returns:
        {count, guests: [{guest_id, name, email, status, registered_at}], has_more}
    """
    params: dict[str, Any] = {
        "event_api_id": event_id,
        "pagination_limit": min(int(limit), 200),
    }
    if status:
        params["approval_status"] = status
    raw = client.get("/event/get-guests", params=params, tool="luma_list_event_guests")
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        entries = []
    guests = [LumaGuest.from_api(g) for g in entries]
    return {
        "count": len(guests),
        "guests": [
            {
                "guest_id": g.guest_id,
                "name": g.name,
                "email": g.email,
                "status": g.status,
                "registered_at": g.registered_at,
            }
            for g in guests
        ],
        "has_more": bool(raw.get("has_more")) if isinstance(raw, dict) else False,
    }
