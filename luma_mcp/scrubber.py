"""Prompt-injection scrubber for user-supplied free-text fields.

Surfaces caller intent if a string contains role-spoof prefixes, fake
fences, or zero-width characters by wrapping the suspicious text in
backticks rather than deleting it. The operator still sees the attempt
in the rendered Luma surface, but it cannot execute against the model
on a downstream read.

Mirror of whatsapp-mcp + slack-mcp scrubber pattern.
"""

from __future__ import annotations

import re
import unicodedata


_INJECT_RE = re.compile(
    r"(?i)\b(?:ignore|forget|disregard)\s+(?:previous|prior|all|the)\s+(?:instruction|rule|prompt)s?\b"
    r"|^\s*(?:system|assistant|user|sudo|tool|developer)\s*:\s*"
    r"|```(?:system|sudo|developer|tool|assistant|user)\b",
    re.MULTILINE,
)


def scrub(text: str | None) -> str:
    if not text:
        return text or ""
    s = unicodedata.normalize("NFKC", text)
    # Strip zero-width chars
    s = "".join(c for c in s if unicodedata.category(c) != "Cf")
    # Wrap suspicious patterns in backticks (don't delete; preserve operator visibility).
    s = _INJECT_RE.sub(lambda m: f"`{m.group(0)}`", s)
    return s
