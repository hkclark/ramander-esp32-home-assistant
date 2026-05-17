"""Tests for the Remander DataUpdateCoordinator."""

from __future__ import annotations

from typing import Any

import pytest
from aioresponses import aioresponses
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.remander.api import RemanderClient
from custom_components.remander.const import DOMAIN
from custom_components.remander.coordinator import RemanderCoordinator

HOST = "192.168.1.42"
STATUS_URL = f"http://{HOST}/api/status"


@pytest.fixture
async def coordinator(hass: HomeAssistant) -> RemanderCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    return RemanderCoordinator(
        hass, entry, RemanderClient(async_get_clientsession(hass), HOST)
    )


async def test_first_refresh_populates(
    coordinator: RemanderCoordinator, status_payload: dict[str, Any]
) -> None:
    with aioresponses() as m:
        m.get(STATUS_URL, payload=status_payload)
        await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert coordinator.data["mode"] == "away"
    assert coordinator.data["device_id"] == "AA:BB:CC:DD:EE:FF"
    assert coordinator.data["firmware_version"] == "1.4.0"


async def test_refresh_failure_raises_update_failed(
    coordinator: RemanderCoordinator,
) -> None:
    with aioresponses() as m:
        m.get(STATUS_URL, exception=TimeoutError("boom"))
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_polling_interval_is_30s(coordinator: RemanderCoordinator) -> None:
    assert coordinator.update_interval.total_seconds() == 30


async def test_apply_push_mode_changed(
    coordinator: RemanderCoordinator, status_payload: dict[str, Any]
) -> None:
    coordinator.async_set_updated_data(dict(status_payload))
    coordinator.apply_push_event(
        "mode_changed", {"from": "away", "to": "home"}, "2026-05-17T12:00:00Z"
    )
    assert coordinator.data["mode"] == "home"


async def test_apply_push_mute_armed_then_expired(
    coordinator: RemanderCoordinator, status_payload: dict[str, Any]
) -> None:
    coordinator.async_set_updated_data(dict(status_payload))
    coordinator.apply_push_event(
        "mute_armed",
        {"mute_until": "2026-05-17T13:00:00Z", "triggered_by": "set_home"},
        "2026-05-17T12:01:00Z",
    )
    assert coordinator.data["muted"] is True
    assert coordinator.data["mute_until"] == "2026-05-17T13:00:00Z"

    coordinator.apply_push_event("mute_expired", {}, "2026-05-17T13:00:00Z")
    assert coordinator.data["muted"] is False
    assert coordinator.data["mute_until"] is None


async def test_apply_push_workflow_complete(
    coordinator: RemanderCoordinator, status_payload: dict[str, Any]
) -> None:
    coordinator.async_set_updated_data(dict(status_payload))
    coordinator.apply_push_event(
        "workflow_complete",
        {
            "workflow": "set_away",
            "result": "success",
            "duration_ms": 1840,
            "failed_step": None,
        },
        "2026-05-17T12:34:56Z",
    )
    last = coordinator.data["last_workflow"]
    assert last["workflow"] == "set_away"
    assert last["result"] == "success"
    assert last["finished_at"] == "2026-05-17T12:34:56Z"
    assert last["duration_ms"] == 1840


async def test_apply_push_event_with_no_baseline(
    coordinator: RemanderCoordinator,
) -> None:
    """An event arriving before the first poll still updates data."""
    coordinator.apply_push_event(
        "mode_changed", {"from": "home", "to": "paused"}, "2026-05-17T00:00:00Z"
    )
    assert coordinator.data["mode"] == "paused"
