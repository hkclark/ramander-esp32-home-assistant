"""Tests for the Remander config flow."""

from __future__ import annotations

from collections.abc import Iterator
from ipaddress import IPv4Address
from typing import Any
from unittest.mock import patch

import pytest
from aioresponses import aioresponses
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.remander.const import (
    CONF_DEVICE_ID,
    CONF_WEBHOOK_ID,
    DOMAIN,
    WEBHOOK_EVENTS,
    WEBHOOK_SCHEMA,
    WEBHOOK_TAG,
)

HOST = "192.168.1.42"
DEVICE_ID = "AA:BB:CC:DD:EE:FF"
STATUS_URL = f"http://{HOST}/api/status"
WEBHOOK_URL = f"http://{HOST}/api/config/notify/url"


@pytest.fixture(autouse=True)
def _external_url(hass: HomeAssistant) -> None:
    """webhook.async_generate_url needs at least one HA URL configured."""
    hass.config.external_url = "http://homeassistant.local:8123"


@pytest.fixture
def mock_device(status_payload: dict[str, Any]) -> Iterator[aioresponses]:
    """Happy-path mock: status returns the fixture, webhook POST returns ok."""
    with aioresponses() as m:
        m.get(STATUS_URL, payload=status_payload, repeat=True)
        m.post(WEBHOOK_URL, payload={"ok": True}, repeat=True)
        yield m


async def _start_user_flow(
    hass: HomeAssistant, *, host: str = HOST, password: str | None = None
) -> dict[str, Any]:
    """Drive the user step to the second async_configure call."""
    init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    user_input: dict[str, Any] = {CONF_HOST: host}
    if password is not None:
        user_input[CONF_PASSWORD] = password
    with patch("custom_components.remander.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            init["flow_id"], user_input=user_input
        )
        await hass.async_block_till_done()
    return result


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_device: aioresponses
) -> None:
    """A user-entered host completes the flow and creates a config entry
    keyed by the firmware-supplied device_id."""
    result = await _start_user_flow(hass)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_DEVICE_ID] == DEVICE_ID
    assert CONF_WEBHOOK_ID in result["data"]
    assert result["result"].unique_id == DEVICE_ID


async def test_user_flow_registers_webhook_on_device(
    hass: HomeAssistant, mock_device: aioresponses
) -> None:
    """The flow POSTs a v2-schema WebhookEntry to the device with our tag."""
    result = await _start_user_flow(hass)
    assert result["type"] == FlowResultType.CREATE_ENTRY

    calls = mock_device.requests.get(("POST", URL(WEBHOOK_URL)))
    assert calls and len(calls) == 1
    body = calls[0].kwargs["json"]
    assert body["tag"] == WEBHOOK_TAG
    assert body["schema"] == WEBHOOK_SCHEMA
    assert body["events"] == WEBHOOK_EVENTS
    assert body["url"].startswith("http://homeassistant.local:8123/api/webhook/")
    assert body["url"].endswith(result["data"][CONF_WEBHOOK_ID])


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Network failure during /api/status surfaces as cannot_connect."""
    with aioresponses() as m:
        m.get(STATUS_URL, exception=TimeoutError("boom"))
        result = await _start_user_flow(hass)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """401 from /api/status surfaces as invalid_auth."""
    with aioresponses() as m:
        m.get(STATUS_URL, status=401)
        result = await _start_user_flow(hass, password="hunter2")

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_duplicate_device_aborts(
    hass: HomeAssistant, mock_device: aioresponses
) -> None:
    """A second flow for the same device_id aborts as already_configured."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        data={CONF_HOST: "192.168.1.99", CONF_DEVICE_ID: DEVICE_ID},
    ).add_to_hass(hass)

    result = await _start_user_flow(hass)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    # Critical: we must NOT have written the webhook to the new host's device.
    assert not mock_device.requests.get(("POST", URL(WEBHOOK_URL)))


def _zeroconf_info(*, device_id_compact: str = "AABBCCDDEEFF") -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=IPv4Address(HOST),
        ip_addresses=[IPv4Address(HOST)],
        port=80,
        hostname="remander.local.",
        type="_remander._tcp.local.",
        name="Remander._remander._tcp.local.",
        properties={
            "id": device_id_compact,
            "model": "remander-esp32",
            "version": "1.4.0",
            "api": "v1",
            "auth": "none",
        },
    )


async def test_zeroconf_discovery_creates_entry(
    hass: HomeAssistant, mock_device: aioresponses
) -> None:
    """A zeroconf-discovered device shows a confirm step, then creates an entry."""
    init = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf_info(),
    )
    assert init["type"] == FlowResultType.FORM
    assert init["step_id"] == "discovery_confirm"

    with patch("custom_components.remander.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            init["flow_id"], user_input={}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_DEVICE_ID] == DEVICE_ID
    assert result["result"].unique_id == DEVICE_ID


async def test_zeroconf_duplicate_device_aborts(
    hass: HomeAssistant, mock_device: aioresponses
) -> None:
    """A zeroconf event for an already-configured device aborts without confirm."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        data={CONF_HOST: "192.168.1.99", CONF_DEVICE_ID: DEVICE_ID},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf_info(),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
