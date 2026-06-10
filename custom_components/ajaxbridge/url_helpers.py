"""URL helpers for Ajaxbridge integration."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def websocket_base_url(bridge_url: str) -> str:
    """Return the WebSocket base URL for an HTTP(S) bridge URL."""
    normalized = bridge_url.rstrip("/")
    parts = urlsplit(normalized)
    if parts.scheme == "https":
        scheme = "wss"
    elif parts.scheme == "http":
        scheme = "ws"
    else:
        scheme = parts.scheme
    return urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))
