"""The Remander integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import webhook as remander_webhook
from .api import RemanderClient, RemanderError
from .const import CONF_DEVICE_ID, CONF_WEBHOOK_ID, DOMAIN, WEBHOOK_TAG
from .coordinator import RemanderCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

SERVICE_SET_MODE = "set_mode"
SERVICE_PAUSE = "pause"
SERVICE_REARM = "rearm"

_SET_MODE_SCHEMA = vol.Schema(
    {vol.Required(CONF_DEVICE_ID): str, vol.Required("mode"): vol.In(["away", "home"])}
)
_PAUSE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required("duration_minutes"): vol.All(int, vol.Range(min=1, max=1440)),
    }
)
_REARM_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_ID): str})


@dataclass
class RemanderData:
    """Per-entry runtime state."""

    coordinator: RemanderCoordinator
    client: RemanderClient


type RemanderEntry = ConfigEntry[RemanderData]


async def async_setup_entry(hass: HomeAssistant, entry: RemanderEntry) -> bool:
    """Set up Remander from a config entry."""
    session = async_get_clientsession(hass)
    client = RemanderClient(
        session,
        entry.data[CONF_HOST],
        password=entry.data.get(CONF_PASSWORD) or None,
    )
    coordinator = RemanderCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    remander_webhook.async_register(hass, entry.data[CONF_WEBHOOK_ID], coordinator)

    entry.runtime_data = RemanderData(coordinator=coordinator, client=client)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RemanderEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        remander_webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
        # Best-effort: remove our entry from the device. The integration is
        # going away whether or not the device is reachable, so swallow errors.
        try:
            await entry.runtime_data.client.async_delete_webhook(WEBHOOK_TAG)
        except RemanderError as err:
            _LOGGER.debug("Could not remove webhook from device on unload: %s", err)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    """Register domain-wide services on first entry setup (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_MODE):
        return

    def _coordinator_for(call: ServiceCall) -> tuple[RemanderClient, str]:
        target_id = call.data[CONF_DEVICE_ID]
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_DEVICE_ID) == target_id and entry.runtime_data:
                return entry.runtime_data.client, target_id
        raise vol.Invalid(f"No loaded Remander matches device_id={target_id!r}")

    async def _set_mode(call: ServiceCall) -> None:
        client, _ = _coordinator_for(call)
        cmd = "away" if call.data["mode"] == "away" else "home"
        await client.async_command(cmd)

    async def _pause(call: ServiceCall) -> None:
        # Firmware uses its own configured default duration today; once it grows
        # a per-call duration parameter we will forward it via the URL.
        client, _ = _coordinator_for(call)
        await client.async_command("pause")

    async def _rearm(call: ServiceCall) -> None:
        client, _ = _coordinator_for(call)
        await client.async_command("rearm")

    hass.services.async_register(DOMAIN, SERVICE_SET_MODE, _set_mode, schema=_SET_MODE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PAUSE, _pause, schema=_PAUSE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REARM, _rearm, schema=_REARM_SCHEMA)
