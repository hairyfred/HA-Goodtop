"""Config flow for Goodtop Switch integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from .const import DEFAULT_USERNAME, DOMAIN
from .coordinator import GoodtopApiClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class GoodtopConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Goodtop Switch."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Test connection
            client = GoodtopApiClient(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )

            if await client.test_connection():
                # Get device info for unique ID
                try:
                    data = await client.get_data()
                    unique_id = data.mac_address.replace(":", "").lower()
                    if unique_id:
                        await self.async_set_unique_id(unique_id)
                        self._abort_if_unique_id_configured()
                except Exception:
                    pass

                title = f"Goodtop Switch ({user_input[CONF_HOST]})"
                return self.async_create_entry(title=title, data=user_input)
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
