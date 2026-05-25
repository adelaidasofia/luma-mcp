"""SSRF mitigation tests for luma-mcp client._request (MYC-101).

LUMA_API_BASE env var lets a malicious operator override the base URL,
which would let any user-controlled `path` reach internal IPs. The
helper rejects before httpx fires.
"""
from __future__ import annotations

import os
import socket
from unittest.mock import patch

import pytest

# Stub LUMA_API_KEY so client doesn't raise from env-missing.
os.environ.setdefault("LUMA_API_KEY", "dummy-key")

from luma_mcp.client import LumaAPIError, _request


class TestSSRFLumaClient:
    def test_rejects_url_with_backslash(self):
        with patch.dict(os.environ, {"LUMA_API_BASE": "https://api.lu.ma/\\bad"}):
            with pytest.raises(LumaAPIError, match="SSRF"):
                _request("GET", "/anything")

    def test_rejects_embedded_credentials(self):
        with patch.dict(os.environ, {"LUMA_API_BASE": "https://u:p@api.lu.ma"}):
            with pytest.raises(LumaAPIError, match="SSRF"):
                _request("GET", "/anything")

    def test_rejects_ipv6_link_local(self):
        with patch.dict(os.environ, {"LUMA_API_BASE": "http://[fe80::1]"}):
            with pytest.raises(LumaAPIError, match="SSRF"):
                _request("GET", "/anything")

    def test_rejects_dns_resolving_to_private_ip(self):
        with patch("mycelium_security.url.socket.getaddrinfo") as mock_resolver:
            mock_resolver.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))
            ]
            with patch.dict(os.environ, {"LUMA_API_BASE": "http://attacker.example.com"}):
                with pytest.raises(LumaAPIError, match="SSRF"):
                    _request("GET", "/anything")

    def test_rejects_aws_metadata_endpoint(self):
        with patch.dict(os.environ, {"LUMA_API_BASE": "http://169.254.169.254"}):
            with pytest.raises(LumaAPIError, match="SSRF"):
                _request("GET", "/latest/meta-data/iam/security-credentials/")

    def test_follow_redirects_false_is_set(self):
        import httpx
        captured = {}

        class _Spy(httpx.Client):
            def __init__(self, *args, **kwargs):
                captured.update(kwargs)
                super().__init__(*args, **kwargs)

        with patch("luma_mcp.client.httpx.Client", _Spy):
            try:
                _request("GET", "/zen")
            except Exception:
                pass
        assert captured.get("follow_redirects") is False
