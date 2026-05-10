"""HTTP client wrapper around the Luma public API.

- Base URL: https://api.lu.ma/public/v1 (override via LUMA_API_BASE).
- Auth: x-luma-api-key header (LUMA_API_KEY env).
- Every request is timed and audit-logged.
- Rate limit (200 req/min/calendar) is the caller's responsibility — this
  client does not retry on 429; it surfaces the error and lets the operator
  pace.

Per Lesson #16 + #17: do not bypass; reuse the client for every endpoint.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from luma_mcp import audit


class LumaAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, payload: Any = None):
        super().__init__(f"Luma API {status_code}: {message}")
        self.status_code = status_code
        self.payload = payload


def _api_key() -> str:
    key = os.environ.get("LUMA_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "LUMA_API_KEY env var not set. Generate at https://lu.ma/settings/api "
            "(requires Luma Plus subscription) and add to ~/.claude/luma-mcp/.env "
            "or export it before launching Claude Code."
        )
    return key


def _base() -> str:
    return os.environ.get("LUMA_API_BASE", "https://api.lu.ma/public/v1").rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "x-luma-api-key": _api_key(),
        "accept": "application/json",
        "content-type": "application/json",
    }


def _request(method: str, path: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None, tool: str = "client") -> dict[str, Any]:
    """Send a request and return the parsed JSON. Audit-logs every call.

    Raises LumaAPIError on non-2xx responses with the API's error body
    preserved on `.payload` for the caller to surface.
    """
    url = f"{_base()}{path if path.startswith('/') else '/' + path}"
    started = time.time()
    status_label = "ok"
    error: str | None = None
    payload: dict[str, Any] = {}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(
                method.upper(),
                url,
                headers=_headers(),
                params=params,
                json=json_body,
            )
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            status_label = f"http_{resp.status_code}"
            err_msg = (
                (isinstance(data, dict) and (data.get("error") or data.get("message"))) or resp.text or "unknown"
            )
            raise LumaAPIError(resp.status_code, str(err_msg)[:300], data)
        payload = data if isinstance(data, dict) else {"data": data}
        return payload
    except LumaAPIError as e:
        error = str(e)
        raise
    except Exception as e:
        status_label = "exception"
        error = f"{type(e).__name__}: {e}"
        raise
    finally:
        latency_ms = (time.time() - started) * 1000
        audit.log(
            tool=tool,
            action=f"{method.upper()} {path}",
            args={"params": params or {}, "json": json_body or {}},
            status=status_label,
            latency_ms=latency_ms,
            error=error,
        )


def get(path: str, *, params: dict[str, Any] | None = None, tool: str = "client") -> dict[str, Any]:
    return _request("GET", path, params=params, tool=tool)


def post(path: str, *, json_body: dict[str, Any] | None = None, tool: str = "client") -> dict[str, Any]:
    return _request("POST", path, json_body=json_body, tool=tool)


def health() -> dict[str, Any]:
    """Cheap auth check. Calls a known-cheap endpoint to validate the API key."""
    # /user/get-self is the canonical "is my key valid" probe per Luma docs.
    try:
        return get("/user/get-self", tool="health")
    except LumaAPIError as e:
        raise
