"""Config Flow: Benutzername und Passwort des WebMenü-Portals."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import MensaAuthError, MensaClient, MensaConnectionError
from .const import DOMAIN


async def _validate(hass, username: str, password: str) -> str | None:
    """Fehlerschlüssel oder None, wenn der Login klappt."""
    client = MensaClient(async_create_clientsession(hass), username, password)
    try:
        await client.async_login()
    except MensaAuthError:
        return "invalid_auth"
    except MensaConnectionError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        return "unknown"
    return None


class MensaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {k: v.strip() for k, v in user_input.items()}
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            error = await _validate(self.hass, user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            if error is None:
                return self.async_create_entry(title="Mensa Schule", data=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await _validate(self.hass, entry.data[CONF_USERNAME], user_input[CONF_PASSWORD])
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )
