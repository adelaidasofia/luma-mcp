"""Ticket type creation. Sets the price on an event."""

from __future__ import annotations

from typing import Any

from luma_mcp import client, drafts
from luma_mcp._shared import LumaTicketType
from luma_mcp.server import mcp


@mcp.tool()
def luma_create_ticket_type_draft(
    event_id: str,
    name: str,
    price_usd: float | None = None,
    cents: int | None = None,
    currency: str = "USD",
    capacity: int | None = None,
    description: str | None = None,
    require_approval: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage a ticket type for an event. Nothing posts until confirm.

    Pass either price_usd (decimal, e.g. 250.0) or cents (integer, e.g. 25000).
    Setting both raises. Setting neither creates a free ticket.
    """
    if price_usd is not None and cents is not None:
        raise ValueError("set price_usd or cents, not both")
    if cents is None and price_usd is not None:
        cents = int(round(price_usd * 100))
    if cents is None:
        cents = 0
    payload: dict[str, Any] = {
        "event_api_id": event_id,
        "name": name,
        "cents": int(cents),
        "currency": currency,
    }
    if capacity is not None:
        payload["capacity"] = int(capacity)
    if description:
        payload["description"] = description
    if require_approval is not None:
        payload["require_approval"] = bool(require_approval)
    if extra:
        payload.update(extra)
    preview = (
        f"CREATE TICKET TYPE\n"
        f"  event_id: {event_id}\n"
        f"  name: {name}\n"
        f"  price: {cents/100:.2f} {currency}\n"
        + (f"  capacity: {capacity}\n" if capacity is not None else "")
    )
    d = drafts.store().stage("create_ticket_type", payload, preview)
    return {"draft_id": d.draft_id, "preview": preview, "expires_at": d.expires_at}


@mcp.tool()
def luma_create_ticket_type_confirm(draft_id: str) -> dict[str, Any]:
    """Commit a previously-drafted ticket type."""

    def _run(d) -> dict[str, Any]:
        if d.kind != "create_ticket_type":
            raise ValueError(f"draft kind mismatch: expected create_ticket_type, got {d.kind}")
        return client.post("/event/ticket-types/create", json_body=d.payload, tool="luma_create_ticket_type_confirm")

    raw = drafts.store().confirm(draft_id, _run)
    tt = LumaTicketType.from_api(raw, event_id=str(_extract(raw, "event_api_id")))
    return {
        "ticket_type_id": tt.ticket_type_id,
        "event_id": tt.event_id,
        "name": tt.name,
        "price": f"{tt.cents/100:.2f} {tt.currency}",
        "raw": raw,
    }


def _extract(payload: Any, key: str) -> str:
    if isinstance(payload, dict):
        if key in payload:
            return str(payload[key])
        for v in payload.values():
            if isinstance(v, dict) and key in v:
                return str(v[key])
    return ""
