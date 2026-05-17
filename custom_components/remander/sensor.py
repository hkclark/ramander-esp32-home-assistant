"""Sensor entities for Remander."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
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
    coord = entry.runtime_data.coordinator
    async_add_entities(
        [ModeSensor(coord), LastWorkflowSensor(coord), UptimeSensor(coord)]
    )


class _SensorBase(CoordinatorEntity[RemanderCoordinator], SensorEntity):
    """Shared device-info + unique-id wiring."""

    _attr_has_entity_name = True

    def __init__(self, coord: RemanderCoordinator, key: str) -> None:
        super().__init__(coord)
        device_id = coord.data.get("device_id", "unknown")
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"Remander ({device_id})",
            manufacturer=MANUFACTURER,
            model=coord.data.get("model", MODEL),
            sw_version=coord.data.get("firmware_version"),
            configuration_url=f"http://{coord.client.host}",
        )


class ModeSensor(_SensorBase):
    """Current away/home/paused mode."""

    _attr_name = "Mode"
    _attr_translation_key = "mode"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["away", "home", "paused", "unknown"]

    def __init__(self, coord: RemanderCoordinator) -> None:
        super().__init__(coord, "mode")

    @property
    def native_value(self) -> str:
        mode = self.coordinator.data.get("mode", "unknown")
        return mode if mode in self._attr_options else "unknown"


class LastWorkflowSensor(_SensorBase):
    """State = workflow name; attributes carry result + finished_at + duration."""

    _attr_name = "Last workflow"
    _attr_translation_key = "last_workflow"

    def __init__(self, coord: RemanderCoordinator) -> None:
        super().__init__(coord, "last_workflow")

    @property
    def native_value(self) -> str | None:
        lw = self.coordinator.data.get("last_workflow")
        return lw.get("workflow") if lw else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lw = self.coordinator.data.get("last_workflow") or {}
        return {
            "result": lw.get("result"),
            "finished_at": lw.get("finished_at"),
            "duration_ms": lw.get("duration_ms"),
            "failed_step": lw.get("failed_step"),
        }


class UptimeSensor(_SensorBase):
    """Seconds since the device booted."""

    _attr_name = "Uptime"
    _attr_translation_key = "uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coord: RemanderCoordinator) -> None:
        super().__init__(coord, "uptime")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("uptime_s")
