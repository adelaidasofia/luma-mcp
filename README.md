# luma-mcp


<!-- mycelium-badges:start -->

<p>
  <a href="https://github.com/adelaidasofia/luma-mcp/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/adelaidasofia/luma-mcp?color=blue"></a>
  <a href="https://github.com/adelaidasofia/luma-mcp/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/adelaidasofia/luma-mcp?color=eab308"></a>
  <a href="https://github.com/adelaidasofia/luma-mcp/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/adelaidasofia/luma-mcp"></a>
  <a href="https://github.com/adelaidasofia/luma-mcp/issues"><img alt="Open issues" src="https://img.shields.io/github/issues/adelaidasofia/luma-mcp"></a>
  <a href="https://pypi.org/project/adelaidasofia-luma-mcp/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/adelaidasofia-luma-mcp?color=blue&label=pypi"></a>
  <a href="https://pypi.org/project/adelaidasofia-luma-mcp/"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/adelaidasofia-luma-mcp?color=blue&label=downloads"></a>
  <a href="https://myceliumai.co"><img alt="Built by Mycelium AI" src="https://img.shields.io/badge/built_by-Mycelium_AI-15B89A"></a>
</p>

<!-- mycelium-badges:end -->

lu.ma events MCP server. Create events, set ticket prices, issue coupon codes, list RSVPs, and email attendees. All writes go through draft+confirm so nothing posts to Luma until you explicitly approve. Built on the official Luma public API.

## What it does

- Create + update lu.ma events (name, date, timezone, capacity, meeting URL, visibility, cover image)
- Set ticket types and pricing
- Issue coupon codes (calendar-scoped or event-scoped, percentage or fixed-cents discounts, redemption caps)
- List event guests / RSVPs
- Send markdown emails to attendees (pre-work, day-of, follow-up)
- Audit log of every API call (JSONL with key/token redaction)
- Prompt-injection scrubber on user-supplied free-text fields

## Tools (v0.1.0)

Reads (call API directly):

- `luma_health` — auth check + draft store size
- `luma_get_event` — fetch one event by ID
- `luma_list_events` — paginated calendar listing
- `luma_list_event_guests` — RSVPs filtered by status
- `luma_list_coupons` — calendar or event-scoped

Writes (draft+confirm pairs):

- `luma_create_event_draft` / `luma_create_event_confirm`
- `luma_update_event_draft` / `luma_update_event_confirm`
- `luma_create_ticket_type_draft` / `luma_create_ticket_type_confirm`
- `luma_create_coupon_draft` / `luma_create_coupon_confirm`
- `luma_send_event_email_draft` / `luma_send_event_email_confirm`

Plus:

- `luma_cancel_draft` — cancel an unconfirmed draft (idempotent)

14 tools total.

## Architecture

```
luma-mcp/
├── pyproject.toml
├── README.md
├── SETUP.md
├── LICENSE
├── .env.example
├── luma_mcp/
│   ├── __init__.py
│   ├── server.py             FastMCP entry point + .env loader
│   ├── client.py             HTTP wrapper around api.lu.ma/public/v1
│   ├── drafts.py             Thread-safe draft store with TTL
│   ├── audit.py              JSONL audit log with redaction
│   ├── scrubber.py           Prompt-injection neutralizer
│   ├── _shared/              Day-1 shared utilities
│   │   ├── normalize.py      Timezone alias + datetime helpers
│   │   └── types.py          Permissive typed shapes for API responses
│   └── tools/
│       ├── health.py         luma_health, luma_cancel_draft
│       ├── events.py         create / update / get / list events
│       ├── tickets.py        create ticket types
│       ├── coupons.py        create / list coupons
│       ├── guests.py         list event guests
│       └── emails.py         send email to attendees
└── tests/integration/
    └── test_full_pipeline.py 10-step bare-runnable verification
```

## Safety patterns

1. **Draft + confirm on every write.** The draft tool returns a `draft_id`; nothing hits Luma until the matching confirm tool is called. Drafts expire after 1 hour and can only be confirmed once.
2. **Audit log.** Every API call is logged JSONL with `ts`, `tool`, `action`, args (redacted), `status`, `latency_ms`. Path: `~/.claude/luma-mcp/audit.log`.
3. **Token redaction.** Strings matching long-key heuristics, or values under keys like `api_key`, `token`, `cookie`, `secret`, are masked before logging.
4. **Prompt-injection scrubber.** User-supplied free-text fields (event name, description, email subject, email body) are passed through `unicodedata.normalize("NFKC")`, stripped of zero-width characters, and have role-spoof prefixes / fake fences wrapped in backticks (preserving operator visibility, neutralizing model effect on downstream reads).
5. **Zero LLM in the tool path.** Every routing decision is rule-based.

## Use cases

- **Workshops + paid events** — set sticker price, issue community-specific 100%-off coupons, pull guest list, blast pre-work email.
- **Multi-event programs** — one cohorte announcement, sub-events on Luma, pull RSVPs across sessions.
- **Recurring meetups** — duplicate event template via update_event_draft, change date, ship.

## Install

Open Claude Code, paste:

    /plugin marketplace add adelaidasofia/luma-mcp
    /plugin install luma-mcp@luma-mcp

Two prerequisites for the server to authenticate:

1. **Luma Plus subscription** on the calendar you'll use (the public API is gated behind Plus).
2. **API key** generated from `https://lu.ma/settings/api`, dropped into `~/.claude/luma-mcp/.env` as `LUMA_API_KEY=...`.

After both steps, restart Claude Code. Tools appear under `mcp__luma__*`.

<details>
<summary>Legacy install</summary>

See `SETUP.md` for the manual `.mcp.json` registration path. The plugin install above replaces it.

</details>

## Verification

```bash
cd ~/.claude/luma-mcp && python3 tests/integration/test_full_pipeline.py
# expected: PASSED — luma-mcp v0.1.0 integration test (10 steps green)
```

Then in a Claude Code session: `mcp__luma__luma_health()` → `{ok: true, user: {...}}`.

## Rate limit

Luma's public API caps at 200 requests / minute / calendar. The client does not auto-retry on 429; it surfaces the error and lets the operator pace.

## Related MCPs

Same author, same architecture pattern (FastMCP, draft+confirm on writes, vault auto-export where applicable):

- [slack-mcp](https://github.com/adelaidasofia/slack-mcp) — multi-workspace Slack
- [imessage-mcp](https://github.com/adelaidasofia/imessage-mcp) — macOS iMessage
- [whatsapp-mcp](https://github.com/adelaidasofia/whatsapp-mcp) — WhatsApp via whatsmeow
- [apollo-mcp](https://github.com/adelaidasofia/apollo-mcp) — Apollo.io CRM + sequences
- [google-workspace-mcp](https://github.com/adelaidasofia/google-workspace-mcp) — Gmail / Calendar / Drive / Docs / Sheets
- [substack-mcp](https://github.com/adelaidasofia/substack-mcp) — Substack writing + analytics
- [parse-mcp](https://github.com/adelaidasofia/parse-mcp) — markitdown / Docling / LlamaParse router


## Telemetry

This plugin sends a single anonymous install signal to `myceliumai.co` the first time it loads in a Claude Code session on a given machine.

**What is sent:**
- Plugin name (e.g. `slack-mcp`)
- Plugin version (e.g. `0.1.0`)

**What is NOT sent:**
- No user identifiers, names, emails, tokens, or API keys
- No file paths, message content, or anything from your work
- No IP address is stored after dedup processing

**Why:** Helps the maintainer know which plugins people actually install, so attention goes to the ones that get used.

**Opt out:** Set the environment variable `MYCELIUM_NO_PING=1` before launching Claude Code. The hook will skip the network call entirely. Already-pinged installs leave a sentinel at `~/.mycelium/onboarded-<plugin>` — delete it if you want to reset state.

## License

MIT. See `LICENSE`.
