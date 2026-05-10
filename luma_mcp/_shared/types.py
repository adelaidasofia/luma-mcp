"""Lightweight typed shapes for Luma API responses.

These are intentionally permissive — Luma adds fields over time, and the
MCP forwards extra fields to the caller via the `raw` dict. Required fields
are typed, the rest stays in `raw` for forward compat without a release
cut every time Luma adds a field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LumaEvent:
    """One Luma event. Extra/new fields stay in `raw`."""

    event_id: str
    name: str
    start_at: str  # ISO-8601 with timezone
    timezone: str  # IANA tz name
    url: str | None = None
    capacity: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "LumaEvent":
        ev = payload.get("event", payload) if isinstance(payload, dict) else {}
        return cls(
            event_id=str(ev.get("api_id") or ev.get("event_id") or ev.get("id") or ""),
            name=str(ev.get("name", "")),
            start_at=str(ev.get("start_at", "")),
            timezone=str(ev.get("timezone", "")),
            url=ev.get("url"),
            capacity=ev.get("max_capacity"),
            raw=ev,
        )


@dataclass
class LumaTicketType:
    ticket_type_id: str
    event_id: str
    name: str
    cents: int  # price in cents (USD assumed unless currency specified)
    currency: str = "USD"
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, payload: dict[str, Any], event_id: str = "") -> "LumaTicketType":
        tt = payload.get("ticket_type", payload) if isinstance(payload, dict) else {}
        return cls(
            ticket_type_id=str(tt.get("api_id") or tt.get("id") or ""),
            event_id=event_id or str(tt.get("event_api_id", "")),
            name=str(tt.get("name", "")),
            cents=int(tt.get("cents", 0) or 0),
            currency=str(tt.get("currency", "USD")),
            raw=tt,
        )


@dataclass
class LumaCoupon:
    coupon_id: str
    code: str
    discount_percentage: int | None = None
    discount_cents: int | None = None
    max_redemptions: int | None = None
    redeemed: int = 0
    event_id: str | None = None  # None = calendar-scoped
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "LumaCoupon":
        c = payload.get("coupon", payload) if isinstance(payload, dict) else {}
        return cls(
            coupon_id=str(c.get("api_id") or c.get("id") or ""),
            code=str(c.get("code", "")),
            discount_percentage=c.get("discount_percentage"),
            discount_cents=c.get("discount_cents"),
            max_redemptions=c.get("max_redemptions"),
            redeemed=int(c.get("num_redeemed", 0) or 0),
            event_id=c.get("event_api_id"),
            raw=c,
        )


@dataclass
class LumaGuest:
    """One RSVP / registered guest."""

    guest_id: str
    name: str
    email: str
    status: str  # going, declined, waitlist, etc.
    registered_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "LumaGuest":
        g = payload
        # Sometimes the guest is nested under "guest" or "user"
        if isinstance(g, dict):
            inner = g.get("guest") or g.get("user")
            if isinstance(inner, dict):
                g = {**g, **inner}
        return cls(
            guest_id=str(g.get("api_id") or g.get("id") or ""),
            name=str(g.get("name") or g.get("user_name") or ""),
            email=str(g.get("email") or g.get("user_email") or ""),
            status=str(g.get("approval_status") or g.get("status") or "unknown"),
            registered_at=g.get("registered_at") or g.get("created_at"),
            raw=g if isinstance(g, dict) else {},
        )
