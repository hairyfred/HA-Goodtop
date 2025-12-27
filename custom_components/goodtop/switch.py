"""Switch platform for Goodtop integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoodtopConfigEntry
from .const import DOMAIN
from .coordinator import GoodtopCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoodtopConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Goodtop switches."""
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = []

    # Create PoE switches for each port (typically only RJ45 ports have PoE)
    for port_id in coordinator.data.ports:
        entities.append(GoodtopPoeSwitch(coordinator, entry, port_id))
        entities.append(GoodtopPortSwitch(coordinator, entry, port_id))

    async_add_entities(entities)


class GoodtopSwitchBase(CoordinatorEntity[GoodtopCoordinator], SwitchEntity):
    """Base class for Goodtop switches."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._port_id = port_id
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for port sub-device."""
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, f"{data.mac_address}_port{self._port_id}")},
            name=f"Port {self._port_id}",
            manufacturer="Goodtop",
            model=data.model,
            via_device=(DOMAIN, data.mac_address),
        )


class GoodtopPoeSwitch(GoodtopSwitchBase):
    """Switch for controlling PoE on a port."""

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the PoE switch."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_poe"
        self._attr_name = "PoE"
        self._attr_icon = "mdi:ethernet"

    @property
    def is_on(self) -> bool:
        """Return true if PoE is enabled."""
        port = self.coordinator.data.ports.get(self._port_id)
        return port.poe_enabled if port else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on PoE."""
        if await self.coordinator.client.set_poe(self._port_id, True):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off PoE."""
        if await self.coordinator.client.set_poe(self._port_id, False):
            await self.coordinator.async_request_refresh()


class GoodtopPortSwitch(GoodtopSwitchBase):
    """Switch for enabling/disabling a port."""

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the port switch."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_enable"
        self._attr_name = "Enabled"
        self._attr_icon = "mdi:ethernet-cable"

    @property
    def is_on(self) -> bool:
        """Return true if port is enabled."""
        port = self.coordinator.data.ports.get(self._port_id)
        return port.state.lower() == "enable" if port else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable port."""
        port = self.coordinator.data.ports.get(self._port_id)
        speed_duplex = port.speed_duplex if port else "0"
        flow_control = port.flow_control if port else "0"
        if await self.coordinator.client.set_port_state(
            self._port_id, True, speed_duplex, flow_control
        ):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable port."""
        port = self.coordinator.data.ports.get(self._port_id)
        speed_duplex = port.speed_duplex if port else "0"
        flow_control = port.flow_control if port else "0"
        if await self.coordinator.client.set_port_state(
            self._port_id, False, speed_duplex, flow_control
        ):
            await self.coordinator.async_request_refresh()
