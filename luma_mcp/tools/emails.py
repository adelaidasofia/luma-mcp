"""Send email to event attendees. Pre-work, day-of Zoom link, follow-up.

Uses draft+confirm: nothing hits Luma until confirm. The body is scrubbed
for prompt injection before send.
"""

from __future__ import annotations

from typing import Any

from luma_mcp import client, drafts, scrubber
from luma_mcp.server import mcp


@mcp.tool()
def luma_send_event_email_draft(
    event_id: str,
    subject: str,
    body_md: str,
    target_audience: str = "going",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage an email blast to event attendees. Body markdown supported.

    Args:
        event_id: Luma event api_id.
        subject: Email subject line.
        body_md: Markdown body. Scrubbed for prompt injection before send.
        target_audience: Which segment. "going" (registered + approved),
                         "all" (all RSVPs), "waitlist", "declined". Default "going".
        extra: Forward-compat additional fields.
    """
    payload: dict[str, Any] = {
        "event_api_id": event_id,
        "subject": scrubber.scrub(subject),
        "body": scrubber.scrub(body_md),
        "target_audience": target_audience,
    }
    if extra:
        payload.update(extra)
    preview = (
        f"SEND EMAIL TO ATTENDEES\n"
        f"  event_id: {event_id}\n"
        f"  audience: {target_audience}\n"
        f"  subject: {payload['subject']}\n"
        f"  body preview ({len(body_md)} chars):\n"
        f"  -----\n"
        f"  {body_md[:400]}{'...' if len(body_md) > 400 else ''}\n"
        f"  -----"
    )
    d = drafts.store().stage("send_email", payload, preview)
    return {"draft_id": d.draft_id, "preview": preview, "expires_at": d.expires_at}


@mcp.tool()
def luma_send_event_email_confirm(draft_id: str) -> dict[str, Any]:
    """Commit a previously-drafted attendee email blast."""

    def _run(d) -> dict[str, Any]:
        if d.kind != "send_email":
            raise ValueError(f"draft kind mismatch: expected send_email, got {d.kind}")
        return client.post("/event/send-email", json_body=d.payload, tool="luma_send_event_email_confirm")

    raw = drafts.store().confirm(draft_id, _run)
    return {"sent": True, "raw": raw}
