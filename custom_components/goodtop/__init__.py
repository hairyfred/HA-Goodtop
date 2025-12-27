"""The Goodtop Switch integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import GoodtopApiClient, GoodtopCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

type GoodtopConfigEntry = ConfigEntry[GoodtopCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GoodtopConfigEntry) -> bool:
    """Set up Goodtop Switch from a config entry."""
    client = GoodtopApiClient(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    coordinator = GoodtopCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register the main switch device first so sub-devices can reference it
    device_registry = dr.async_get(hass)
    data = coordinator.data
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, data.mac_address)},
        name=f"Goodtop {data.model}" if data.model else "Goodtop Switch",
        manufacturer="Goodtop",
        model=data.model,
        sw_version=data.firmware_version,
        hw_version=data.hardware_version,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GoodtopConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
