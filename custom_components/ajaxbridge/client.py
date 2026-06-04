"""Client for ajaxbridge server."""

from __future__ import annotations

from typing import Any

import aiohttp


class AjaxbridgeApiError(RuntimeError):
    """Raised when ajaxbridge returns a structured HTTP error."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


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
            await _raise_for_api_error(response)
            return await response.json()

    async def create_claim(
        self,
        *,
        hub_id: str,
        hub_name: str | None = None,
        hub_model: str | None = None,
    ) -> dict[str, Any]:
        """Create a self-service hub claim."""
        return await self._post_json(
            "/api/v1/me/claims",
            {
                "hub_id": hub_id,
                "hub_name": hub_name,
                "hub_model": hub_model,
            },
        )

    async def list_claims(self) -> dict[str, Any]:
        """List self-service claims for this installation."""
        return await self._get_json("/api/v1/me/claims")

    async def verify_claim(self, claim_id: str) -> dict[str, Any]:
        """Ask the bridge to verify a claim against stored Ajax events."""
        return await self._post_json(f"/api/v1/me/claims/{claim_id}/verify", {})

    async def complete_claim(self, claim_id: str) -> dict[str, Any]:
        """Complete a verified claim and create membership."""
        return await self._post_json(f"/api/v1/me/claims/{claim_id}/complete", {})

    async def list_memberships(self) -> dict[str, Any]:
        """List memberships for this installation."""
        return await self._get_json("/api/v1/me/memberships")

    async def enable_membership(self, membership_id: str) -> dict[str, Any]:
        """Enable a membership."""
        return await self._post_json(f"/api/v1/me/memberships/{membership_id}/enable", {})

    async def disable_membership(self, membership_id: str) -> dict[str, Any]:
        """Disable a membership."""
        return await self._post_json(f"/api/v1/me/memberships/{membership_id}/disable", {})

    @property
    def installation_id(self) -> str:
        """Return installation id."""
        return self._installation_id

    async def _get_json(self, path: str) -> dict[str, Any]:
        url = f"{self._bridge_url}{path}"
        async with self._session.get(
            url,
            headers={"Authorization": f"Bearer {self._api_token}"},
        ) as response:
            await _raise_for_api_error(response)
            return await response.json()

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._bridge_url}{path}"
        async with self._session.post(
            url,
            headers={"Authorization": f"Bearer {self._api_token}"},
            json=payload,
        ) as response:
            await _raise_for_api_error(response)
            return await response.json()

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


async def _raise_for_api_error(response: aiohttp.ClientResponse) -> None:
    """Raise an error that preserves FastAPI's JSON detail field."""
    if response.status < 400:
        return
    detail = response.reason
    try:
        payload = await response.json()
    except (aiohttp.ContentTypeError, ValueError):
        payload = None
    if isinstance(payload, dict) and payload.get("detail"):
        detail = str(payload["detail"])
    raise AjaxbridgeApiError(response.status, detail)
