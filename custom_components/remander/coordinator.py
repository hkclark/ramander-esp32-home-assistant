"""DataUpdateCoordinator for Remander devices."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RemanderClient, RemanderError
from .const import DEFAULT_POLL_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RemanderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /api/status on a 30s interval; also applies pushed webhook events."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: RemanderClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_status()
        except RemanderError as err:
            raise UpdateFailed(str(err)) from err

    def apply_push_event(
        self, event_type: str, event_data: dict[str, Any], timestamp: str
    ) -> None:
        """Merge a pushed webhook event into the latest status snapshot.

        Drives instant entity updates so users don't wait up to 30s for the
        next poll to reflect a mode change or mute window.
        """
        data: dict[str, Any] = dict(self.data) if self.data else {}

        if event_type == "mode_changed":
            data["mode"] = event_data.get("to", data.get("mode"))
        elif event_type == "mute_armed":
            data["muted"] = True
            data["mute_until"] = event_data.get("mute_until")
        elif event_type == "mute_expired":
            data["muted"] = False
            data["mute_until"] = None
        elif event_type == "workflow_complete":
            data["last_workflow"] = {
                "workflow": event_data.get("workflow"),
                "result": event_data.get("result"),
                "finished_at": timestamp,
                "duration_ms": event_data.get("duration_ms"),
                "failed_step": event_data.get("failed_step"),
            }

        self.async_set_updated_data(data)
