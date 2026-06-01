"""Client for ajaxbridge server."""

from __future__ import annotations

from typing import Any

import aiohttp


class AjaxbridgeClient:
    """Small HTTP client for ajaxbridge."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        bridge_url: str,
        installation_id: str,
        api_token: str,
    ) -> None:
        self._session = session
        self._bridge_url = bridge_url.rstrip("/")
        self._installation_id = installation_id
        self._api_token = api_token

    async def get_state_model(self) -> dict[str, Any]:
        """Fetch the current installation state model."""
        url = f"{self._bridge_url}/api/v1/installations/{self._installation_id}/state-model"
        async with self._session.get(
            url,
            headers={"Authorization": f"Bearer {self._api_token}"},
        ) as response:
            response.raise_for_status()
            return await response.json()

    @property
    def installation_id(self) -> str:
        """Return installation id."""
        return self._installation_id

    async def connect_ws(self) -> aiohttp.ClientWebSocketResponse:
        """Open an authenticated WebSocket connection."""
        ws_url = self._bridge_url.replace("https://", "wss://").replace("http://", "ws://")
        ws = await self._session.ws_connect(f"{ws_url}/api/v1/ws")
        await ws.send_json(
            {
                "type": "auth",
                "installation_id": self._installation_id,
                "token": self._api_token,
            }
        )
        auth = await ws.receive_json()
        if auth.get("type") != "auth_ok":
            await ws.close()
            raise RuntimeError(f"Ajaxbridge auth failed: {auth}")
        return ws
