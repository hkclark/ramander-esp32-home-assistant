"""Tests for the Remander webhook handler."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.remander import webhook as remander_webhook
from custom_components.remander.api import RemanderClient
from custom_components.remander.const import (
    DOMAIN,
    EVENT_MODE_CHANGED,
    EVENT_MUTE_ARMED,
    EVENT_WORKFLOW_COMPLETE,
)
from custom_components.remander.coordinator import RemanderCoordinator

WEBHOOK_ID = "remander_test_webhook"
WEBHOOK_PATH = f"/api/webhook/{WEBHOOK_ID}"
DEVICE_ID = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
async def setup(
    hass: HomeAssistant, status_payload: dict[str, Any]
) -> RemanderCoordinator:
    await async_setup_component(hass, "webhook", {})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "192.168.1.42"})
    entry.add_to_hass(hass)
    coordinator = RemanderCoordinator(
        hass, entry, RemanderClient(async_get_clientsession(hass), "192.168.1.42")
    )
    coordinator.async_set_updated_data(dict(status_payload))
    remander_webhook.async_register(hass, WEBHOOK_ID, coordinator)
    return coordinator


async def test_workflow_complete_fires_event(
    hass: HomeAssistant, hass_client_no_auth, setup: RemanderCoordinator
) -> None:
    events = async_capture_events(hass, EVENT_WORKFLOW_COMPLETE)
    http = await hass_client_no_auth()
    resp = await http.post(
        WEBHOOK_PATH,
        json={
            "schema": "v2",
            "event_type": "workflow_complete",
            "timestamp": "2026-05-17T12:34:56Z",
            "device_id": DEVICE_ID,
            "data": {
                "workflow": "set_away",
                "result": "success",
                "duration_ms": 1840,
                "failed_step": None,
            },
        },
    )
    assert resp.status == 200
    assert len(events) == 1
    assert events[0].data["workflow"] == "set_away"
    assert events[0].data["result"] == "success"
    assert events[0].data["device_id"] == DEVICE_ID
    assert setup.data["last_workflow"]["workflow"] == "set_away"


async def test_mode_changed_updates_coordinator_and_fires_event(
    hass: HomeAssistant, hass_client_no_auth, setup: RemanderCoordinator
) -> None:
    events = async_capture_events(hass, EVENT_MODE_CHANGED)
    http = await hass_client_no_auth()
    resp = await http.post(
        WEBHOOK_PATH,
        json={
            "schema": "v2",
            "event_type": "mode_changed",
            "timestamp": "2026-05-17T12:00:00Z",
            "device_id": DEVICE_ID,
            "data": {"from": "away", "to": "home"},
        },
    )
    assert resp.status == 200
    assert setup.data["mode"] == "home"
    assert len(events) == 1
    assert events[0].data["to"] == "home"
    assert events[0].data["from"] == "away"


async def test_mute_armed_updates_coordinator(
    hass: HomeAssistant, hass_client_no_auth, setup: RemanderCoordinator
) -> None:
    events = async_capture_events(hass, EVENT_MUTE_ARMED)
    http = await hass_client_no_auth()
    resp = await http.post(
        WEBHOOK_PATH,
        json={
            "schema": "v2",
            "event_type": "mute_armed",
            "timestamp": "2026-05-17T12:00:00Z",
            "device_id": DEVICE_ID,
            "data": {
                "mute_until": "2026-05-17T13:00:00Z",
                "triggered_by": "set_home",
            },
        },
    )
    assert resp.status == 200
    assert setup.data["muted"] is True
    assert setup.data["mute_until"] == "2026-05-17T13:00:00Z"
    assert len(events) == 1


async def test_malformed_json_returns_400(
    hass: HomeAssistant, hass_client_no_auth, setup: RemanderCoordinator
) -> None:
    http = await hass_client_no_auth()
    resp = await http.post(
        WEBHOOK_PATH, data="not json at all", headers={"Content-Type": "text/plain"}
    )
    assert resp.status == 400


async def test_v1_payload_ignored_silently(
    hass: HomeAssistant, hass_client_no_auth, setup: RemanderCoordinator
) -> None:
    """Legacy ntfy.sh-style payloads are for humans; we drop them with 204."""
    events_complete = async_capture_events(hass, EVENT_WORKFLOW_COMPLETE)
    events_mode = async_capture_events(hass, EVENT_MODE_CHANGED)
    http = await hass_client_no_auth()
    resp = await http.post(
        WEBHOOK_PATH,
        json={"title": "Remander: set_away", "message": "set_away completed"},
    )
    assert resp.status == 204
    assert events_complete == []
    assert events_mode == []


async def test_unknown_event_type_returns_204(
    hass: HomeAssistant, hass_client_no_auth, setup: RemanderCoordinator
) -> None:
    http = await hass_client_no_auth()
    resp = await http.post(
        WEBHOOK_PATH,
        json={
            "schema": "v2",
            "event_type": "future_event_we_dont_know",
            "timestamp": "2026-05-17T12:00:00Z",
            "device_id": DEVICE_ID,
            "data": {},
        },
    )
    assert resp.status == 204
