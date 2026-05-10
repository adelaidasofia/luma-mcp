# luma-mcp setup

## 1. Luma Plus subscription

The Luma public API requires an active **Luma Plus** subscription on the calendar whose API key you'll use. Without Plus, every API call returns a 401 / 403.

- Subscribe at [lu.ma/pricing](https://lu.ma/pricing).
- Plus is per-calendar. If you have multiple calendars, decide which one this MCP will manage. The API key you generate is scoped to that calendar — events, tickets, coupons, and guests all live on that calendar.

## 2. Generate API key

1. Open `https://lu.ma/settings/api` while logged in to the Plus calendar.
2. Click **Generate New API Key**.
3. Copy the key. You will not be shown it again.

## 3. Drop the key into `.env`

```bash
cd ~/.claude/luma-mcp
cp .env.example .env
```

Edit `.env`:

```
LUMA_API_KEY=your-actual-key-here
```

Optional overrides (rarely needed):

```
# LUMA_API_BASE=https://api.lu.ma/public/v1   # default
# LUMA_AUDIT_LOG=/path/to/audit.log           # default ~/.claude/luma-mcp/audit.log
# LUMA_DRAFT_TTL=3600                         # default 1h
```

The server reads `.env` on startup and falls back to OS env vars.

## 4. Install dependencies

The server uses FastMCP and httpx. If you have FastMCP installed globally (which you do — it's how every other MCP in this vault runs), you also need httpx:

```bash
python3 -m pip install --break-system-packages 'httpx>=0.27'
```

Verify:

```bash
python3 -c "import fastmcp, httpx; print('fastmcp', fastmcp.__version__, '· httpx', httpx.__version__)"
```

## 5. Run integration test

```bash
cd ~/.claude/luma-mcp && python3 tests/integration/test_full_pipeline.py
```

Expected:

```
PASSED — luma-mcp v0.1.0 integration test (10 steps green)
```

This test runs without any live API calls. It validates module imports, draft store cycles, scrubber, audit log redaction, type shape parsing, and timezone normalization.

## 6. Registration (already done)

The MCP is registered in your vault `.mcp.json` as `luma`:

```json
"luma": {
  "type": "stdio",
  "command": "fastmcp",
  "args": ["run", "/Users/YOU/.claude/luma-mcp/luma_mcp/server.py"]
}
```

Replace `/Users/YOU/` with your home directory.

No env block in `.mcp.json` — keys live in `~/.claude/luma-mcp/.env` to avoid leaking through `claude mcp list` output.

## 7. Restart Claude Code

```bash
# Quit and relaunch Claude Code from the vault
```

After restart, run `mcp__luma__luma_health()` in a session. Expected:

```json
{
  "ok": true,
  "user": {
    "name": "Your Name",
    "email": "you@example.com",
    "api_id": "user_..."
  },
  "active_drafts": 0
}
```

If `ok: false` with an auth error: re-check that the API key in `.env` matches what `lu.ma/settings/api` shows, and that the calendar still has an active Plus subscription.

## 8. First end-to-end use

Create the Dreamers & Doers May 20 workshop:

```python
# 1. Stage event
luma_create_event_draft(
    name="Build Your AI Second Brain",
    start_at="2026-05-20T14:00:00-04:00",
    timezone="America/New_York",
    end_at="2026-05-20T17:00:00-04:00",
    description_md="<paste the Luma description from Workshop - Dreamers Doers May 20.md>",
    max_capacity=50,
    meeting_url="https://zoom.us/j/...",  # add when you have it
    visibility="public",
)
# returns draft_id

# 2. Confirm event
luma_create_event_confirm(draft_id="luma_xxxxxxxxxxxxxxxx")
# returns event_id, url

# 3. Stage $250 ticket
luma_create_ticket_type_draft(
    event_id="<event_id from step 2>",
    name="General Admission",
    price_usd=250.0,
)
luma_create_ticket_type_confirm(draft_id="luma_yyyyyyyyyyyyyyyy")

# 4. Stage DREAMERS coupon
luma_create_coupon_draft(
    code="DREAMERS",
    discount_percentage=100,
    max_redemptions=30,
    description="Reserved for Dreamers & Doers community members",
)
luma_create_coupon_confirm(draft_id="luma_zzzzzzzzzzzzzzzz")

# 5. Verify
luma_get_event(event_id="<event_id>")
luma_list_coupons()  # should include DREAMERS

# 6. Mon May 11: send pre-work
luma_send_event_email_draft(
    event_id="<event_id>",
    subject="Pre-work for Wednesday — 15 minutes today saves us 30 in the room",
    body_md="<paste pre-work body from Workshop tracker ASSET 6>",
    target_audience="going",
)
luma_send_event_email_confirm(draft_id="luma_aaaaaaaaaaaaaaaa")
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `LUMA_API_KEY env var not set` | Add to `~/.claude/luma-mcp/.env`. Restart Claude Code so the server reloads. |
| `Luma API 401: invalid api key` | Key was rotated or copied wrong. Generate a fresh one at lu.ma/settings/api. |
| `Luma API 403: subscription required` | Calendar is not on Luma Plus, or Plus expired. Renew at lu.ma/pricing. |
| `Luma API 429: rate limit` | 200 req/min/calendar. Slow down. |
| Tools don't appear after restart | Check `claude mcp list` from the vault. If `luma` is missing, run `python3 -c "import json; json.load(open('/path/to/vault/.mcp.json'))"` to rule out malformed JSON. |
| `draft expired` | TTL is 1h. Re-stage the draft. |

## Audit log

Every API call appends one JSON line to `~/.claude/luma-mcp/audit.log`. To inspect:

```bash
tail -n 20 ~/.claude/luma-mcp/audit.log | python3 -m json.tool
```

API keys and token-shaped values are redacted before write.
