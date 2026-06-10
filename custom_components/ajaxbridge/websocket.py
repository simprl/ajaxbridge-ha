"""WebSocket runtime loop for Ajaxbridge."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from .coordinator import AjaxbridgeCoordinator

_LOGGER = logging.getLogger(__name__)


async def ws_loop(coordinator: AjaxbridgeCoordinator) -> None:
    """Maintain the ajaxbridge WebSocket subscription."""
    while True:
        try:
            ws = await coordinator.client.connect_ws()
            coordinator.mark_ws_connected()
            await ws.send_json(
                {
                    "id": 1,
                    "type": "subscribe",
                    "streams": ["entity_state", "source_event", "availability"],
                }
            )
            async for message in ws:
                coordinator.mark_ws_message()
                if message.type != aiohttp.WSMsgType.TEXT:
                    continue
                payload = message.json()
                if payload.get("type") != "event":
                    continue
                coordinator.mark_ws_event()
                if payload.get("stream") == "entity_state":
                    coordinator.apply_entity_state(payload.get("event") or {})
                elif payload.get("stream") == "availability":
                    await coordinator.async_request_refresh()
        except asyncio.CancelledError:
            coordinator.mark_ws_disconnected("cancelled")
            raise
        except Exception as err:
            reason = _exception_reason(err)
            coordinator.mark_ws_disconnected(reason)
            if _should_log_ws_warning(err, reason):
                _LOGGER.warning("Ajaxbridge WebSocket disconnected: %s", reason)
            else:
                _LOGGER.debug("Ajaxbridge WebSocket disconnected: %s", reason)
            await asyncio.sleep(5)


def _exception_reason(err: Exception) -> str:
    """Return a compact non-empty exception reason."""
    return str(err).strip() or err.__class__.__name__


def _should_log_ws_warning(err: Exception, reason: str) -> bool:
    """Return whether a WebSocket reconnect reason deserves warning-level logs."""
    if isinstance(err, TimeoutError):
        return False
    return reason not in {"TimeoutError", "ConnectionResetError"}
