"""Coupon create + list. Calendar-scoped (default) or event-scoped."""

from __future__ import annotations

from typing import Any

from luma_mcp import client, drafts
from luma_mcp._shared import LumaCoupon
from luma_mcp.server import mcp


@mcp.tool()
def luma_create_coupon_draft(
    code: str,
    discount_percentage: int | None = None,
    discount_cents: int | None = None,
    max_redemptions: int | None = None,
    event_id: str | None = None,
    expires_at: str | None = None,
    description: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage a coupon. Nothing posts until confirm.

    Pass exactly one of discount_percentage or discount_cents.
    """
    if discount_percentage is None and discount_cents is None:
        raise ValueError("set discount_percentage or discount_cents")
    if discount_percentage is not None and discount_cents is not None:
        raise ValueError("set exactly one of discount_percentage or discount_cents")
    if discount_percentage is not None and not (0 <= int(discount_percentage) <= 100):
        raise ValueError("discount_percentage must be 0-100")

    payload: dict[str, Any] = {"code": code.upper().strip()}
    if discount_percentage is not None:
        payload["discount_percentage"] = int(discount_percentage)
    if discount_cents is not None:
        payload["discount_cents"] = int(discount_cents)
    if max_redemptions is not None:
        payload["max_redemptions"] = int(max_redemptions)
    if event_id:
        payload["event_api_id"] = event_id
    if expires_at:
        payload["expires_at"] = expires_at
    if description:
        payload["description"] = description
    if extra:
        payload.update(extra)
    discount_str = (
        f"{discount_percentage}% off" if discount_percentage is not None
        else f"{discount_cents/100:.2f} off"
    )
    preview = (
        f"CREATE COUPON\n"
        f"  code: {payload['code']}\n"
        f"  discount: {discount_str}\n"
        + (f"  max_redemptions: {max_redemptions}\n" if max_redemptions is not None else "")
        + (f"  scope: event={event_id}\n" if event_id else "  scope: calendar (any event)\n")
    )
    d = drafts.store().stage("create_coupon", payload, preview)
    return {"draft_id": d.draft_id, "preview": preview, "expires_at": d.expires_at}


@mcp.tool()
def luma_create_coupon_confirm(draft_id: str) -> dict[str, Any]:
    """Commit a previously-drafted coupon."""

    def _run(d) -> dict[str, Any]:
        if d.kind != "create_coupon":
            raise ValueError(f"draft kind mismatch: expected create_coupon, got {d.kind}")
        if d.payload.get("event_api_id"):
            return client.post("/event/coupons/create", json_body=d.payload, tool="luma_create_coupon_confirm")
        return client.post("/calendar/coupons/create", json_body=d.payload, tool="luma_create_coupon_confirm")

    raw = drafts.store().confirm(draft_id, _run)
    c = LumaCoupon.from_api(raw)
    return {
        "coupon_id": c.coupon_id,
        "code": c.code,
        "discount_percentage": c.discount_percentage,
        "discount_cents": c.discount_cents,
        "max_redemptions": c.max_redemptions,
        "raw": raw,
    }


@mcp.tool()
def luma_list_coupons(event_id: str | None = None) -> dict[str, Any]:
    """List coupons scoped to an event (or calendar-wide if event_id is None)."""
    if event_id:
        raw = client.get("/event/coupons", params={"event_api_id": event_id}, tool="luma_list_coupons")
    else:
        raw = client.get("/calendar/coupons", tool="luma_list_coupons")
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        entries = []
    coupons = [LumaCoupon.from_api(c) for c in entries]
    return {
        "count": len(coupons),
        "coupons": [
            {
                "code": c.code,
                "discount_percentage": c.discount_percentage,
                "discount_cents": c.discount_cents,
                "max_redemptions": c.max_redemptions,
                "redeemed": c.redeemed,
                "event_id": c.event_id,
            }
            for c in coupons
        ],
        "raw": raw,
    }
