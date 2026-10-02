"""Mensa Schule – Guthaben, Speiseplan und Bestellstatus aus dem WebMenü-Portal."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import MensaClient
from .coordinator import MensaCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

MensaConfigEntry = ConfigEntry[MensaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MensaConfigEntry) -> bool:
    # Eigene Session mit eigenem Cookie-Jar, damit die Anmeldung erhalten bleibt
    session = async_create_clientsession(hass)
    client = MensaClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = MensaCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MensaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
