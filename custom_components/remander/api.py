"""HTTP client for Remander devices."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import DEFAULT_TIMEOUT_SECONDS

_LOGGER = logging.getLogger(__name__)


class RemanderError(Exception):
    """Base exception for the Remander client."""


class RemanderAuthError(RemanderError):
    """The device rejected the credentials."""


class RemanderConnectionError(RemanderError):
    """The device couldn't be reached or returned an unexpected response."""


class RemanderClient:
    """Async client for the Remander REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        password: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._session = session
        self._host = host
        self._password = password
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def host(self) -> str:
        return self._host

    @property
    def base_url(self) -> str:
        return f"http://{self._host}"

    def _auth(self) -> aiohttp.BasicAuth | None:
        if self._password:
            return aiohttp.BasicAuth("admin", self._password)
        return None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> aiohttp.ClientResponse:
        try:
            resp = await self._session.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                auth=self._auth(),
                timeout=self._timeout,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RemanderConnectionError(str(err)) from err
        if resp.status == 401:
            raise RemanderAuthError("authentication failed")
        if resp.status >= 400:
            raise RemanderConnectionError(f"HTTP {resp.status} from {path}")
        return resp

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch GET /api/status."""
        resp = await self._request("GET", "/api/status")
        return await resp.json()

    async def async_register_webhook(
        self,
        tag: str,
        url: str,
        schema: str,
        events: list[str],
    ) -> None:
        """POST a WebhookEntry to /api/config/notify/url (idempotent by tag)."""
        body = {
            "tag": tag,
            "url": url,
            "schema": schema,
            "events": events,
        }
        await self._request("POST", "/api/config/notify/url", json=body)

    async def async_delete_webhook(self, tag: str) -> None:
        """Remove our webhook entry from the device by tag."""
        await self._request(
            "DELETE", "/api/config/notify/url", params={"tag": tag}
        )

    async def async_command(self, cmd: str) -> None:
        """POST /api/cmd/{cmd}."""
        await self._request("POST", f"/api/cmd/{cmd}")
