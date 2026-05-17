"""Config flow for the Remander integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import RemanderAuthError, RemanderClient, RemanderConnectionError
from .const import (
    CONF_DEVICE_ID,
    CONF_WEBHOOK_ID,
    DOMAIN,
    WEBHOOK_EVENTS,
    WEBHOOK_SCHEMA,
    WEBHOOK_TAG,
)

_LOGGER = logging.getLogger(__name__)

_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


def normalize_device_id(raw: str) -> str:
    """Render a MAC as AA:BB:CC:DD:EE:FF.

    Accepts the colon-separated form from /api/status as well as the compact
    form used in mDNS TXT records. Returns the input unchanged for any value
    that doesn't look like a 48-bit MAC so callers can detect malformed IDs.
    """
    hex_only = raw.replace(":", "").replace("-", "").upper()
    if len(hex_only) != 12 or not all(c in "0123456789ABCDEF" for c in hex_only):
        return raw
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))


class RemanderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Remander."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._password: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manual host entry."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_USER_SCHEMA)
        self._host = user_input[CONF_HOST]
        self._password = user_input.get(CONF_PASSWORD) or None
        return await self._validate_and_create()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle a Remander device discovered via _remander._tcp.local."""
        raw_id = discovery_info.properties.get("id", "")
        if isinstance(raw_id, bytes):
            raw_id = raw_id.decode("utf-8", errors="replace")
        device_id = normalize_device_id(raw_id) if raw_id else ""
        if not device_id or ":" not in device_id:
            return self.async_abort(reason="not_remander")

        await self.async_set_unique_id(device_id)
        host = str(discovery_info.ip_address)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._host = host
        self.context["title_placeholders"] = {
            "name": f"Remander ({device_id})",
        }
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show a one-button confirmation card after zeroconf discovery."""
        if user_input is None:
            return self.async_show_form(
                step_id="discovery_confirm",
                description_placeholders={
                    "host": self._host or "",
                    "device_id": self.unique_id or "",
                },
            )
        return await self._validate_and_create()

    async def _validate_and_create(self) -> FlowResult:
        """Fetch status, register the webhook on the device, create the entry."""
        assert self._host is not None
        session = async_get_clientsession(self.hass)
        client = RemanderClient(session, self._host, password=self._password)

        errors: dict[str, str] = {}
        try:
            status = await client.async_get_status()
        except RemanderAuthError:
            errors["base"] = "invalid_auth"
        except RemanderConnectionError:
            errors["base"] = "cannot_connect"
        else:
            device_id = normalize_device_id(status["device_id"])
            if self.unique_id is None:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
            elif self.unique_id != device_id:
                # TXT-record id didn't match the device's reported device_id.
                # Should not happen with healthy firmware, but bail rather than
                # write conflicting state.
                return self.async_abort(reason="mismatched_device")

            webhook_id = webhook.async_generate_id()
            webhook_url = webhook.async_generate_url(self.hass, webhook_id)
            try:
                await client.async_register_webhook(
                    tag=WEBHOOK_TAG,
                    url=webhook_url,
                    schema=WEBHOOK_SCHEMA,
                    events=WEBHOOK_EVENTS,
                )
            except (RemanderConnectionError, RemanderAuthError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Remander ({device_id})",
                    data={
                        CONF_HOST: self._host,
                        CONF_PASSWORD: self._password or "",
                        CONF_DEVICE_ID: device_id,
                        CONF_WEBHOOK_ID: webhook_id,
                    },
                )

        if self.source == config_entries.SOURCE_ZEROCONF:
            return self.async_show_form(step_id="discovery_confirm", errors=errors)
        return self.async_show_form(
            step_id="user", data_schema=_USER_SCHEMA, errors=errors
        )
