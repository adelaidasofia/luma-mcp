"""Event create / update / get / list tools.

Create + update use draft+confirm. Get + list are direct reads.
"""

from __future__ import annotations

from typing import Any

from luma_mcp import client, drafts, scrubber
from luma_mcp._shared import LumaEvent, iana_timezone_for, parse_iso_datetime
from luma_mcp.server import mcp


def _shape_event_payload(
    *,
    name: str,
    start_at: str,
    timezone: str,
    end_at: str | None,
    description_md: str | None,
    max_capacity: int | None,
    meeting_url: str | None,
    visibility: str | None,
    require_approval: bool | None,
    cover_image_url: str | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": scrubber.scrub(name),
        "start_at": start_at,
        "timezone": iana_timezone_for(timezone),
    }
    if end_at:
        payload["end_at"] = end_at
    if description_md:
        payload["description_md"] = scrubber.scrub(description_md)
    if max_capacity is not None:
        payload["max_capacity"] = int(max_capacity)
    if meeting_url:
        payload["meeting_url"] = meeting_url
    if visibility:
        payload["visibility"] = visibility
    if require_approval is not None:
        payload["require_approval"] = bool(require_approval)
    if cover_image_url:
        payload["cover_url"] = cover_image_url
    if extra:
        payload.update(extra)
    return payload


@mcp.tool()
def luma_create_event_draft(
    name: str,
    start_at: str,
    timezone: str,
    end_at: str | None = None,
    description_md: str | None = None,
    max_capacity: int | None = None,
    meeting_url: str | None = None,
    visibility: str | None = None,
    require_approval: bool | None = None,
    cover_image_url: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage an event for creation. Nothing posts to Luma until confirm.

    Args:
        name: Event title.
        start_at: ISO-8601 datetime with timezone offset (e.g. 2026-05-20T14:00:00-04:00).
        timezone: IANA tz name (America/New_York) or alias (ET, EDT, NY, Bogotá).
        end_at: ISO-8601 datetime, optional.
        description_md: Markdown body. Scrubbed for prompt injection before send.
        max_capacity: Hard attendance cap.
        meeting_url: Zoom/Meet/etc. URL for virtual events.
        visibility: "public" or "private". Default per calendar settings.
        require_approval: If true, RSVPs need host approval.
        cover_image_url: Cover image URL (must already be hosted).
        extra: Additional Luma-supported fields not enumerated above.

    Returns: dict with draft_id, preview, expires_at.
    """
    parse_iso_datetime(start_at)
    if end_at:
        parse_iso_datetime(end_at)
    payload = _shape_event_payload(
        name=name, start_at=start_at, timezone=timezone, end_at=end_at,
        description_md=description_md, max_capacity=max_capacity,
        meeting_url=meeting_url, visibility=visibility,
        require_approval=require_approval, cover_image_url=cover_image_url,
        extra=extra,
    )
    preview = (
        f"CREATE EVENT\n"
        f"  name: {payload['name']}\n"
        f"  start: {payload['start_at']} ({payload['timezone']})\n"
        + (f"  end: {payload['end_at']}\n" if "end_at" in payload else "")
        + (f"  capacity: {payload['max_capacity']}\n" if "max_capacity" in payload else "")
        + (f"  meeting_url: {payload['meeting_url']}\n" if "meeting_url" in payload else "")
        + (f"  visibility: {payload['visibility']}\n" if "visibility" in payload else "")
    )
    d = drafts.store().stage("create_event", payload, preview)
    return {"draft_id": d.draft_id, "preview": preview, "expires_at": d.expires_at}


@mcp.tool()
def luma_create_event_confirm(draft_id: str) -> dict[str, Any]:
    """Commit a previously-drafted event creation. Returns the new event."""

    def _run(d) -> dict[str, Any]:
        if d.kind != "create_event":
            raise ValueError(f"draft kind mismatch: expected create_event, got {d.kind}")
        return client.post("/event/create", json_body=d.payload, tool="luma_create_event_confirm")

    raw = drafts.store().confirm(draft_id, _run)
    ev = LumaEvent.from_api(raw)
    return {"event_id": ev.event_id, "name": ev.name, "url": ev.url, "raw": raw}


@mcp.tool()
def luma_update_event_draft(
    event_id: str,
    name: str | None = None,
    start_at: str | None = None,
    timezone: str | None = None,
    end_at: str | None = None,
    description_md: str | None = None,
    max_capacity: int | None = None,
    meeting_url: str | None = None,
    visibility: str | None = None,
    cover_image_url: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage an event update. Only fields provided are changed."""
    payload: dict[str, Any] = {"event_api_id": event_id}
    if name is not None:
        payload["name"] = scrubber.scrub(name)
    if start_at is not None:
        parse_iso_datetime(start_at)
        payload["start_at"] = start_at
    if timezone is not None:
        payload["timezone"] = iana_timezone_for(timezone)
    if end_at is not None:
        parse_iso_datetime(end_at)
        payload["end_at"] = end_at
    if description_md is not None:
        payload["description_md"] = scrubber.scrub(description_md)
    if max_capacity is not None:
        payload["max_capacity"] = int(max_capacity)
    if meeting_url is not None:
        payload["meeting_url"] = meeting_url
    if visibility is not None:
        payload["visibility"] = visibility
    if cover_image_url is not None:
        payload["cover_url"] = cover_image_url
    if extra:
        payload.update(extra)
    preview = f"UPDATE EVENT {event_id}\n" + "\n".join(f"  {k}: {v}" for k, v in payload.items() if k != "event_api_id")
    d = drafts.store().stage("update_event", payload, preview)
    return {"draft_id": d.draft_id, "preview": preview, "expires_at": d.expires_at}


@mcp.tool()
def luma_update_event_confirm(draft_id: str) -> dict[str, Any]:
    """Commit a previously-drafted event update."""

    def _run(d) -> dict[str, Any]:
        if d.kind != "update_event":
            raise ValueError(f"draft kind mismatch: expected update_event, got {d.kind}")
        return client.post("/event/update", json_body=d.payload, tool="luma_update_event_confirm")

    raw = drafts.store().confirm(draft_id, _run)
    return {"updated": True, "raw": raw}


@mcp.tool()
def luma_get_event(event_id: str) -> dict[str, Any]:
    """Fetch one event by ID. Returns the typed shape plus the raw payload."""
    raw = client.get("/event/get", params={"api_id": event_id}, tool="luma_get_event")
    ev = LumaEvent.from_api(raw)
    return {
        "event_id": ev.event_id,
        "name": ev.name,
        "start_at": ev.start_at,
        "timezone": ev.timezone,
        "url": ev.url,
        "capacity": ev.capacity,
        "raw": raw,
    }


@mcp.tool()
def luma_list_events(after: str | None = None, before: str | None = None, limit: int = 50) -> dict[str, Any]:
    """List events on the API key's calendar. Pagination via after/before cursors."""
    params: dict[str, Any] = {"pagination_limit": min(int(limit), 100)}
    if after:
        params["after"] = after
    if before:
        params["before"] = before
    raw = client.get("/calendar/list-events", params=params, tool="luma_list_events")
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        entries = []
    return {
        "count": len(entries),
        "events": [
            {
                "event_id": LumaEvent.from_api(e).event_id,
                "name": LumaEvent.from_api(e).name,
                "start_at": LumaEvent.from_api(e).start_at,
                "url": LumaEvent.from_api(e).url,
            }
            for e in entries
        ],
        "has_more": bool(raw.get("has_more")) if isinstance(raw, dict) else False,
        "raw": raw,
    }
