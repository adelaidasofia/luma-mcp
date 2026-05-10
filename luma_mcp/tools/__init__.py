"""Tool modules. Each module registers its tools via @mcp.tool() against
the FastMCP instance imported from luma_mcp.server.

Importing this package triggers tool registration as a side effect — that's
the FastMCP idiom (decorator at import time). server.py imports the tool
modules in dependency order.
"""
