"""Datetime + timezone normalization helpers.

Luma's API expects ISO-8601 datetimes with timezone offsets and IANA
timezone names. This module handles common-input formats so the caller
can pass natural strings and have them normalized correctly.
"""

from __future__ import annotations

import datetime as _dt


# Common informal aliases → IANA tz names. Not exhaustive; the API rejects
# unknown tz names so we fall back to passing through whatever the caller
# provided if they used a name not in this map.
_TZ_ALIASES = {
    "et": "America/New_York",
    "edt": "America/New_York",
    "est": "America/New_York",
    "eastern": "America/New_York",
    "ny": "America/New_York",
    "nyc": "America/New_York",
    "pt": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "ct": "America/Chicago",
    "cdt": "America/Chicago",
    "cst": "America/Chicago",
    "mt": "America/Denver",
    "mdt": "America/Denver",
    "mst": "America/Denver",
    "bogota": "America/Bogota",
    "bogotá": "America/Bogota",
    "co": "America/Bogota",
    "colombia": "America/Bogota",
    "utc": "UTC",
    "gmt": "UTC",
}


def iana_timezone_for(label: str) -> str:
    """Return an IANA tz string for a friendly label.

    Pass-through if the label already looks like an IANA name (contains a
    slash or is exactly UTC). Otherwise look up in the aliases table; if
    not found, return the input unchanged so the caller sees a clear API
    error rather than a silent rewrite.
    """
    if not label:
        return label
    s = label.strip()
    if "/" in s or s == "UTC":
        return s
    return _TZ_ALIASES.get(s.lower(), s)


def parse_iso_datetime(value: str) -> _dt.datetime:
    """Parse an ISO-8601 string. Raises ValueError on bad input."""
    if not isinstance(value, str) or not value:
        raise ValueError("empty datetime string")
    s = value.strip()
    # Python 3.11+ handles `Z` suffix natively; older versions need a swap.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return _dt.datetime.fromisoformat(s)


def iso_utc(dt: _dt.datetime | None = None) -> str:
    """Return an ISO-8601 UTC string. Defaults to now."""
    d = dt if dt is not None else _dt.datetime.now(_dt.timezone.utc)
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
