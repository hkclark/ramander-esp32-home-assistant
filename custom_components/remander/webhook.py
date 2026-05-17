"""Push-event webhook handler for Remander devices."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp.web import Request, Response
from homeassistant.components import webhook
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    EVENT_COMMAND_REJECTED,
    EVENT_MODE_CHANGED,
    EVENT_MUTE_ARMED,
    EVENT_MUTE_EXPIRED,
    EVENT_WORKFLOW_COMPLETE,
)
from .coordinator import RemanderCoordinator

_LOGGER = logging.getLogger(__name__)

_EVENT_MAP = {
    "workflow_complete": EVENT_WORKFLOW_COMPLETE,
    "mode_changed": EVENT_MODE_CHANGED,
    "mute_armed": EVENT_MUTE_ARMED,
    "mute_expired": EVENT_MUTE_EXPIRED,
    "command_rejected": EVENT_COMMAND_REJECTED,
}


def async_register(
    hass: HomeAssistant,
    webhook_id: str,
    coordinator: RemanderCoordinator,
) -> None:
    """Register the HA webhook that receives Remander push events."""

    async def _handle(
        hass: HomeAssistant, webhook_id: str, request: Request
    ) -> Response:
        try:
            payload = await request.json()
        except Exception as err:  # noqa: BLE001 — aiohttp raises ValueError or json.JSONDecodeError
            _LOGGER.warning("Remander webhook: malformed JSON: %s", err)
            return Response(status=400)
        return _process(hass, coordinator, payload)

    webhook.async_register(hass, DOMAIN, "Remander", webhook_id, _handle)


def async_unregister(hass: HomeAssistant, webhook_id: str) -> None:
    """Reverse of async_register, called from async_unload_entry."""
    webhook.async_unregister(hass, webhook_id)


def _process(
    hass: HomeAssistant,
    coordinator: RemanderCoordinator,
    payload: Any,
) -> Response:
    """Dispatch one v2-schema event to the coordinator and the HA bus."""
    if not isinstance(payload, dict) or payload.get("schema") != "v2":
        # v1 (legacy ntfy.sh-style) payloads are for humans, not us.
        _LOGGER.debug("Remander webhook: ignoring non-v2 payload")
        return Response(status=204)

    event_type = payload.get("event_type", "")
    ha_event = _EVENT_MAP.get(event_type)
    if ha_event is None:
        _LOGGER.warning("Remander webhook: unknown event_type %r", event_type)
        return Response(status=204)

    timestamp = payload.get("timestamp", "")
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    coordinator.apply_push_event(event_type, data, timestamp)
    hass.bus.async_fire(
        ha_event,
        {
            "device_id": payload.get("device_id"),
            "timestamp": timestamp,
            **data,
        },
    )
    return Response(status=200)
