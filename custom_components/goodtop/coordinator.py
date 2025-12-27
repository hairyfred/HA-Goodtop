"""Data coordinator for Goodtop Switch."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class PortData:
    """Data for a single port."""

    id: int
    state: str  # "Enable" or "Disable"
    link: str  # "Up", "Down", or speed like "1000M"
    tx_good: int = 0
    tx_bad: int = 0
    rx_good: int = 0
    rx_bad: int = 0
    poe_enabled: bool = False


@dataclass
class GoodtopData:
    """Data from Goodtop switch."""

    model: str = ""
    mac_address: str = ""
    ip_address: str = ""
    firmware_version: str = ""
    hardware_version: str = ""
    poe_total_watts: float = 0.0
    ports: dict[int, PortData] = field(default_factory=dict)


class GoodtopApiClient:
    """API client for Goodtop switch."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """Initialize the API client."""
        self.host = host.rstrip("/")
        if not self.host.startswith("http"):
            self.host = f"http://{self.host}"
        self.username = username
        self.password = password
        self._cookie = self._generate_cookie()

    def _generate_cookie(self) -> str:
        """Generate auth cookie from username and password."""
        login_combo = f"{self.username}{self.password}"
        return hashlib.md5(login_combo.encode()).hexdigest()

    async def _login(self, session: aiohttp.ClientSession) -> bool:
        """Perform login to establish session."""
        try:
            login_data = {
                "username": self.username,
                "password": self.password,
                "language": "EN",
                "Response": self._cookie,
            }
            _LOGGER.warning("Logging in to %s", self.host)
            async with session.post(
                f"{self.host}/login.cgi",
                data=login_data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                _LOGGER.warning("Login response: %s", response.status)
                return response.status == 200
        except Exception as err:
            _LOGGER.error("Login error: %s", err)
            return False

    async def test_connection(self) -> bool:
        """Test connection to the switch."""
        try:
            async with aiohttp.ClientSession() as session:
                cookies = {"admin": self._cookie}
                async with session.get(
                    f"{self.host}/info.cgi",
                    cookies=cookies,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        return "Device Model" in text or "MAC Address" in text
                    return False
        except Exception:
            return False

    async def get_data(self) -> GoodtopData:
        """Fetch all data from the switch."""
        data = GoodtopData()
        cookies = {"admin": self._cookie}

        async with aiohttp.ClientSession(cookies=cookies) as session:
            # Get system info
            await self._fetch_system_info(session, data)
            # Get PoE total power
            await self._fetch_poe_system(session, data)
            # Get port stats
            await self._fetch_port_stats(session, data)
            # Get PoE port states
            await self._fetch_poe_ports(session, data)

        return data

    async def _fetch_system_info(
        self, session: aiohttp.ClientSession, data: GoodtopData
    ) -> None:
        """Fetch system information."""
        try:
            async with session.get(
                f"{self.host}/info.cgi",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    data.model = self._extract_value(html, "Device Model")
                    data.mac_address = self._extract_value(html, "MAC Address")
                    data.ip_address = self._extract_value(html, "IP Address")
                    data.firmware_version = self._extract_value(html, "Firmware Version")
                    data.hardware_version = self._extract_value(html, "Hardware Version")
        except Exception as err:
            _LOGGER.debug("Error fetching system info: %s", err)

    async def _fetch_poe_system(
        self, session: aiohttp.ClientSession, data: GoodtopData
    ) -> None:
        """Fetch PoE system power."""
        try:
            async with session.get(
                f"{self.host}/pse_system.cgi",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    match = re.search(r'name="pse_con_pwr" value="([\d.]+)"', html)
                    if match:
                        data.poe_total_watts = float(match.group(1))
        except Exception as err:
            _LOGGER.debug("Error fetching PoE system: %s", err)

    async def _fetch_port_stats(
        self, session: aiohttp.ClientSession, data: GoodtopData
    ) -> None:
        """Fetch port statistics."""
        try:
            async with session.get(
                f"{self.host}/port.cgi?page=stats",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    # Parse port rows
                    pattern = (
                        r"<tr>\s*<td>(Port\s*\d+)</td>\s*"
                        r"<td>([^<]+)</td>\s*"
                        r"<td>([^<]+)</td>\s*"
                        r"<td>(\d+)</td>\s*"
                        r"<td>(\d+)</td>\s*"
                        r"<td>(\d+)</td>\s*"
                        r"<td>(\d+)</td>"
                    )
                    for match in re.finditer(pattern, html, re.MULTILINE):
                        port_id = int(re.search(r"\d+", match.group(1)).group(0))
                        data.ports[port_id] = PortData(
                            id=port_id,
                            state=match.group(2).strip(),
                            link=match.group(3).strip(),
                            tx_good=int(match.group(4)),
                            tx_bad=int(match.group(5)),
                            rx_good=int(match.group(6)),
                            rx_bad=int(match.group(7)),
                        )
        except Exception as err:
            _LOGGER.debug("Error fetching port stats: %s", err)

    async def _fetch_poe_ports(
        self, session: aiohttp.ClientSession, data: GoodtopData
    ) -> None:
        """Fetch PoE port states."""
        try:
            async with session.get(
                f"{self.host}/pse_port.cgi",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    # Parse PoE states - look for checked radio buttons or select values
                    # Pattern for finding port PoE state from form
                    for port_id in data.ports:
                        # Look for state indication for each port
                        # The page typically has forms or indicators per port
                        enabled_pattern = rf'portid["\s]*[=:]\s*["\']?{port_id}["\']?.*?state["\s]*[=:]\s*["\']?1'
                        disabled_pattern = rf'portid["\s]*[=:]\s*["\']?{port_id}["\']?.*?state["\s]*[=:]\s*["\']?0'

                        # Try alternative patterns for table-based display
                        if re.search(rf'Port\s*{port_id}.*?Enable', html, re.IGNORECASE | re.DOTALL):
                            data.ports[port_id].poe_enabled = True
                        elif re.search(rf'Port\s*{port_id}.*?Disable', html, re.IGNORECASE | re.DOTALL):
                            data.ports[port_id].poe_enabled = False
        except Exception as err:
            _LOGGER.debug("Error fetching PoE ports: %s", err)

    def _extract_value(self, html: str, label: str) -> str:
        """Extract value from HTML table row."""
        pattern = rf"<th[^>]*>{re.escape(label)}</th>\s*<td[^>]*>([^<]+)</td>"
        match = re.search(pattern, html, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    async def set_poe(self, port_id: int, enabled: bool) -> bool:
        """Set PoE state for a port."""
        try:
            async with aiohttp.ClientSession(cookies={"admin": self._cookie}) as session:
                # Login first to establish session
                await self._login(session)
                data = {
                    "portid": str(port_id),
                    "state": "1" if enabled else "0",
                    "submit": "Apply",
                    "cmd": "poe",
                    "language": "EN",
                }
                _LOGGER.warning("set_poe request: port=%d, state=%s", port_id, enabled)
                async with session.post(
                    f"{self.host}/pse_port.cgi",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    text = await response.text()
                    _LOGGER.warning("set_poe response: %s, body=%s", response.status, text[:500])
                    return response.status == 200
        except Exception as err:
            _LOGGER.error("Error setting PoE for port %d: %s", port_id, err)
            return False

    async def set_port_state(self, port_id: int, enabled: bool) -> bool:
        """Set port enable/disable state."""
        try:
            async with aiohttp.ClientSession(cookies={"admin": self._cookie}) as session:
                # Login first to establish session
                await self._login(session)
                data = {
                    "portid": str(port_id),
                    "state": "1" if enabled else "0",
                    "submit": "+++Apply+++",
                    "cmd": "port",
                    "language": "EN",
                }
                _LOGGER.warning("set_port_state request: port=%d, state=%s", port_id, enabled)
                async with session.post(
                    f"{self.host}/port.cgi",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    text = await response.text()
                    _LOGGER.warning("set_port_state response: %s, body=%s", response.status, text[:500])
                    return response.status == 200
        except Exception as err:
            _LOGGER.error("Error setting port %d state: %s", port_id, err)
            return False


class GoodtopCoordinator(DataUpdateCoordinator[GoodtopData]):
    """Coordinator for Goodtop switch data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GoodtopApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> GoodtopData:
        """Fetch data from the switch."""
        try:
            return await self.client.get_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with switch: {err}") from err
