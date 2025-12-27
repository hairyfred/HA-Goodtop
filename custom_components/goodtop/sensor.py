"""Sensor platform for Goodtop integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfPower
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
    """Set up Goodtop sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    # Total PoE power sensor
    entities.append(GoodtopPoePowerSensor(coordinator, entry))

    # Per-port traffic sensors (diagnostic)
    for port_id in coordinator.data.ports:
        entities.append(GoodtopPortTxGoodSensor(coordinator, entry, port_id))
        entities.append(GoodtopPortTxBadSensor(coordinator, entry, port_id))
        entities.append(GoodtopPortRxGoodSensor(coordinator, entry, port_id))
        entities.append(GoodtopPortRxBadSensor(coordinator, entry, port_id))
        entities.append(GoodtopPortSpeedDuplexSensor(coordinator, entry, port_id))
        entities.append(GoodtopPortFlowControlSensor(coordinator, entry, port_id))

    async_add_entities(entities)


class GoodtopSensorBase(CoordinatorEntity[GoodtopCoordinator], SensorEntity):
    """Base class for Goodtop sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry

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


class GoodtopPoePowerSensor(GoodtopSensorBase):
    """Sensor for total PoE power consumption."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
    ) -> None:
        """Initialize the PoE power sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.data.mac_address}_poe_power"
        self._attr_name = "PoE Power"

    @property
    def native_value(self) -> float:
        """Return the total PoE power."""
        return self.coordinator.data.poe_total_watts


class GoodtopPortSensorBase(GoodtopSensorBase):
    """Base class for per-port sensors."""

    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the port sensor."""
        super().__init__(coordinator, entry)
        self._port_id = port_id

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


class GoodtopPortTxGoodSensor(GoodtopPortSensorBase):
    """Sensor for port TX good packets."""

    _attr_icon = "mdi:upload-network"

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the TX good sensor."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_tx_good"
        self._attr_name = "TX Good"

    @property
    def native_value(self) -> int:
        """Return TX good packet count."""
        port = self.coordinator.data.ports.get(self._port_id)
        return port.tx_good if port else 0


class GoodtopPortTxBadSensor(GoodtopPortSensorBase):
    """Sensor for port TX bad packets."""

    _attr_icon = "mdi:upload-network-outline"

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the TX bad sensor."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_tx_bad"
        self._attr_name = "TX Bad"

    @property
    def native_value(self) -> int:
        """Return TX bad packet count."""
        port = self.coordinator.data.ports.get(self._port_id)
        return port.tx_bad if port else 0


class GoodtopPortRxGoodSensor(GoodtopPortSensorBase):
    """Sensor for port RX good packets."""

    _attr_icon = "mdi:download-network"

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the RX good sensor."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_rx_good"
        self._attr_name = "RX Good"

    @property
    def native_value(self) -> int:
        """Return RX good packet count."""
        port = self.coordinator.data.ports.get(self._port_id)
        return port.rx_good if port else 0


class GoodtopPortRxBadSensor(GoodtopPortSensorBase):
    """Sensor for port RX bad packets."""

    _attr_icon = "mdi:download-network-outline"

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the RX bad sensor."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_rx_bad"
        self._attr_name = "RX Bad"

    @property
    def native_value(self) -> int:
        """Return RX bad packet count."""
        port = self.coordinator.data.ports.get(self._port_id)
        return port.rx_bad if port else 0


SPEED_DUPLEX_MAP = {
    "0": "Auto",
    "1": "10M Half",
    "2": "10M Full",
    "3": "100M Half",
    "4": "100M Full",
    "5": "1000M Full",
}


class GoodtopPortSpeedDuplexSensor(GoodtopPortSensorBase):
    """Sensor for port speed/duplex setting."""

    _attr_icon = "mdi:speedometer"
    _attr_state_class = None  # Not a measurement

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the speed/duplex sensor."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_speed_duplex"
        self._attr_name = "Speed/Duplex"

    @property
    def native_value(self) -> str:
        """Return speed/duplex setting."""
        port = self.coordinator.data.ports.get(self._port_id)
        if port:
            return SPEED_DUPLEX_MAP.get(port.speed_duplex, f"Unknown ({port.speed_duplex})")
        return "Unknown"


class GoodtopPortFlowControlSensor(GoodtopPortSensorBase):
    """Sensor for port flow control setting."""

    _attr_icon = "mdi:swap-horizontal"
    _attr_state_class = None  # Not a measurement

    def __init__(
        self,
        coordinator: GoodtopCoordinator,
        entry: GoodtopConfigEntry,
        port_id: int,
    ) -> None:
        """Initialize the flow control sensor."""
        super().__init__(coordinator, entry, port_id)
        self._attr_unique_id = f"{coordinator.data.mac_address}_port{port_id}_flow_control"
        self._attr_name = "Flow Control"

    @property
    def native_value(self) -> str:
        """Return flow control setting."""
        port = self.coordinator.data.ports.get(self._port_id)
        if port:
            return "Enabled" if port.flow_control == "1" else "Disabled"
        return "Unknown"
