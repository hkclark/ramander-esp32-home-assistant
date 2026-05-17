"""End-to-end tests for setup, entities, services, and unload."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

import pytest
from aioresponses import aioresponses
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.remander.const import (
    CONF_DEVICE_ID,
    CONF_WEBHOOK_ID,
    DOMAIN,
)

HOST = "192.168.1.42"
DEVICE_ID = "AA:BB:CC:DD:EE:FF"
WEBHOOK_ID = "remander_test_webhook"
STATUS_URL = f"http://{HOST}/api/status"
DELETE_WEBHOOK_URL = f"http://{HOST}/api/config/notify/url"
CMD_URL_RE = re.compile(rf"http://{re.escape(HOST)}/api/cmd/[a-z]+")


@pytest.fixture
async def integration(
    hass: HomeAssistant, status_payload: dict[str, Any]
) -> AsyncIterator[tuple[MockConfigEntry, aioresponses]]:
    """Fully set up the integration with mocked HTTP."""
    hass.config.external_url = "http://homeassistant.local:8123"
    await async_setup_component(hass, "webhook", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        data={
            CONF_HOST: HOST,
            CONF_PASSWORD: "",
            CONF_DEVICE_ID: DEVICE_ID,
            CONF_WEBHOOK_ID: WEBHOOK_ID,
        },
    )
    entry.add_to_hass(hass)

    with aioresponses() as m:
        m.get(STATUS_URL, payload=status_payload, repeat=True)
        m.post(CMD_URL_RE, payload={"ok": True}, repeat=True)
        m.delete(
            DELETE_WEBHOOK_URL,
            payload={"ok": True},
            repeat=True,
        )
        # aioresponses matches DELETE with query string against the bare URL
        m.delete(
            f"{DELETE_WEBHOOK_URL}?tag=home_assistant",
            payload={"ok": True},
            repeat=True,
        )
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        try:
            yield entry, m
        finally:
            # Avoid a 10s teardown waiting for the coordinator's next poll to
            # time out against real network after the aioresponses context
            # exits. Idempotent: skip if a test already unloaded.
            if entry.state == ConfigEntryState.LOADED:
                await hass.config_entries.async_unload(entry.entry_id)
                await hass.async_block_till_done()


async def test_setup_creates_expected_entities(
    hass: HomeAssistant, integration
) -> None:
    entry, _ = integration
    assert entry.state == ConfigEntryState.LOADED

    # Sensors
    mode = hass.states.get("sensor.remander_aa_bb_cc_dd_ee_ff_mode")
    assert mode is not None
    assert mode.state == "away"

    last_wf = hass.states.get("sensor.remander_aa_bb_cc_dd_ee_ff_last_workflow")
    assert last_wf is not None

    # Binary sensor
    muted = hass.states.get(
        "binary_sensor.remander_aa_bb_cc_dd_ee_ff_muted"
    )
    assert muted is not None
    assert muted.state == "off"
    assert muted.attributes["mute_until"] is None

    # Buttons exist (state is timestamp of last press, or "unknown")
    for key in ("set_away", "set_home", "pause", "rearm"):
        eid = f"button.remander_aa_bb_cc_dd_ee_ff_{key}"
        assert hass.states.get(eid) is not None, f"missing {eid}"


async def test_button_press_calls_command_endpoint(
    hass: HomeAssistant, integration
) -> None:
    _, m = integration
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.remander_aa_bb_cc_dd_ee_ff_set_away"},
        blocking=True,
    )
    calls = m.requests.get(("POST", URL(f"http://{HOST}/api/cmd/away")))
    assert calls and len(calls) == 1


async def test_service_set_mode_calls_command(
    hass: HomeAssistant, integration
) -> None:
    _, m = integration
    await hass.services.async_call(
        DOMAIN,
        "set_mode",
        {"device_id": DEVICE_ID, "mode": "home"},
        blocking=True,
    )
    calls = m.requests.get(("POST", URL(f"http://{HOST}/api/cmd/home")))
    assert calls and len(calls) == 1


async def test_unload_removes_webhook_and_calls_delete(
    hass: HomeAssistant, integration
) -> None:
    entry, m = integration

    # Webhook handlers are stored in hass.data["webhook"] keyed by id.
    webhooks = hass.data.get("webhook", {})
    assert WEBHOOK_ID in webhooks, "webhook should be registered after setup"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    assert WEBHOOK_ID not in hass.data.get("webhook", {})

    # And we attempted DELETE on the device.
    delete_calls = m.requests.get(
        ("DELETE", URL(f"{DELETE_WEBHOOK_URL}?tag=home_assistant"))
    ) or m.requests.get(("DELETE", URL(DELETE_WEBHOOK_URL)))
    assert delete_calls, "expected DELETE to be sent to device on unload"


async def test_diagnostics_redacts_sensitive_keys(
    hass: HomeAssistant, integration
) -> None:
    from custom_components.remander.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry, _ = integration
    diag = await async_get_config_entry_diagnostics(hass, entry)
    # webhook_id should be redacted; status should still be present
    assert diag["entry_data"][CONF_WEBHOOK_ID] == "**REDACTED**"
    assert diag["status"]["device_id"] == DEVICE_ID
    assert diag["status"]["mode"] == "away"
