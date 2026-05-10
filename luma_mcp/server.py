"""FastMCP entry point.

Imports register tools as a side effect: `from luma_mcp.tools import ...`
triggers the @mcp.tool() decorators in each module.
"""

from __future__ import annotations

import os
import sys

from fastmcp import FastMCP

from luma_mcp import __version__

# Optional: load .env if it exists at the package root, before tools that
# depend on env vars are imported.
def _load_env_file() -> None:
    from pathlib import Path

    candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.home() / ".claude" / "luma-mcp" / ".env",
    ]
    for p in candidates:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
            except Exception:
                pass
            break


_load_env_file()

# Create the FastMCP instance BEFORE tool modules import it.
mcp: FastMCP = FastMCP(
    name="luma",
    instructions=(
        "lu.ma events MCP. Use luma_health() to verify auth. "
        "Read tools (get/list) call the API directly. Write tools "
        "(create event, ticket type, coupon, send email) use draft+confirm: "
        "draft tool returns a draft_id, then confirm tool with that draft_id "
        "actually posts to Luma. Drafts expire after 1 hour. "
        "Cancel an unconfirmed draft via luma_cancel_draft(draft_id)."
    ),
)

# Register tools by importing the modules. Order does not matter — each
# module decorates its tools independently.
from luma_mcp.tools import health  # noqa: E402,F401
from luma_mcp.tools import events  # noqa: E402,F401
from luma_mcp.tools import tickets  # noqa: E402,F401
from luma_mcp.tools import coupons  # noqa: E402,F401
from luma_mcp.tools import guests  # noqa: E402,F401
from luma_mcp.tools import emails  # noqa: E402,F401


def main() -> None:
    print(f"luma-mcp v{__version__} starting", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
