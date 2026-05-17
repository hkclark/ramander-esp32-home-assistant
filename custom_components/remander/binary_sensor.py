"""Binary sensor entities for Remander."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RemanderEntry
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import RemanderCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemanderEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MutedBinarySensor(entry.runtime_data.coordinator)])


class MutedBinarySensor(
    CoordinatorEntity[RemanderCoordinator], BinarySensorEntity
):
    """True while a mute window suppresses notifications on the device."""

    _attr_has_entity_name = True
    _attr_name = "Muted"
    _attr_translation_key = "muted"

    def __init__(self, coord: RemanderCoordinator) -> None:
        super().__init__(coord)
        device_id = coord.data.get("device_id", "unknown")
        self._attr_unique_id = f"{device_id}_muted"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"Remander ({device_id})",
            manufacturer=MANUFACTURER,
            model=coord.data.get("model", MODEL),
        )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("muted"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"mute_until": self.coordinator.data.get("mute_until")}
