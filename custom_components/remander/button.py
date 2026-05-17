"""Button entities for Remander commands."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RemanderEntry
from .api import RemanderClient
from .const import DOMAIN, MANUFACTURER, MODEL

# (translation_key, display_name, /api/cmd/<endpoint>)
_BUTTONS: list[tuple[str, str, str]] = [
    ("set_away", "Set away", "away"),
    ("set_home", "Set home", "home"),
    ("pause", "Pause", "pause"),
    ("rearm", "Rearm", "rearm"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemanderEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = entry.runtime_data
    device_id = data.coordinator.data.get("device_id", "unknown")
    model = data.coordinator.data.get("model", MODEL)
    async_add_entities(
        CommandButton(data.client, device_id, model, key, name, cmd)
        for key, name, cmd in _BUTTONS
    )


class CommandButton(ButtonEntity):
    """Press → POST /api/cmd/{cmd}."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: RemanderClient,
        device_id: str,
        model: str,
        key: str,
        name: str,
        cmd: str,
    ) -> None:
        self._client = client
        self._cmd = cmd
        self._attr_name = name
        self._attr_translation_key = key
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"Remander ({device_id})",
            manufacturer=MANUFACTURER,
            model=model,
        )

    async def async_press(self) -> None:
        await self._client.async_command(self._cmd)
