"""Binary sensor platform for Goodtop integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoodtopConfigEntry
from .const import DOMAIN
from .coordinator import GoodtopCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoodtopConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Goodtop binary sensors."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []

    # Link status for each port
    for port_id in coordinator.data.ports:
        entities.append(GoodtopPortLinkSensor(coordinator, entry, port_id))

    async_add_entities(entities)


class GoodtopPortLinkSensor(CoordinatorEntity[GoodtopCoordinator], BinarySensorEntity):
    """Binary sensor for port link status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the link sensor."""
        super().__init__(coordinator)
        self._port_id = port_id
        self._entry = entry
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_link"
        self._attr_name = f"Port {port_id} Link"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, data.mac_address)},
            name=f"Goodtop {data.model}" if data.model else "Goodtop Switch",
            manufacturer="Goodtop",
            model=data.model,
            sw_version=data.firmware_version,
            hw_version=data.hardware_version,
        )

    @property
    def is_on(self) -> bool:
        """Return true if port link is up."""
        port = self.coordinator.data.ports.get(self._port_id)
        if port:
            # Link is up if it shows a speed (like "1000M") or "Up"
            link = port.link.lower()
            return link != "down" and link != ""
        return False

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return additional attributes."""
        port = self.coordinator.data.ports.get(self._port_id)
        if port:
            return {"link_speed": port.link}
        return {}
