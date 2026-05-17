"""Diagnostics dump for a Remander config entry."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import RemanderEntry
from .const import CONF_WEBHOOK_ID

_REDACT = {CONF_PASSWORD, CONF_WEBHOOK_ID, "auth_token", "password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RemanderEntry
) -> dict[str, Any]:
    coord = entry.runtime_data.coordinator
    return {
        "entry_data": async_redact_data(dict(entry.data), _REDACT),
        "status": dict(coord.data) if coord.data else None,
        "last_update_success": coord.last_update_success,
    }
