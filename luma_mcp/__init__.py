"""luma-mcp: lu.ma events MCP server.

Wraps the official Luma public API (api.lu.ma/public/v1) with FastMCP.
Read tools call the API directly. Write tools (event creation, ticket types,
coupons, attendee emails) go through the draft+confirm pattern: nothing
hits Luma's servers until confirm_draft is called with the draft_id.

Auth: x-luma-api-key header. Requires Luma Plus subscription on the calendar
whose API key you use.
"""

__version__ = "0.1.0"
