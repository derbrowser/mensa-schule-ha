"""DataUpdateCoordinator für Mensa Schule."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import MensaAuthError, MensaClient, MensaConnectionError, MensaData
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MensaCoordinator(DataUpdateCoordinator[MensaData]):
    """Holt alle 30 Minuten Guthaben und Speiseplan; wirft um Mitternacht die Sensoren neu an."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: MensaClient) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL
        )
        self.client = client
        # "Heute"/"Morgen" ändern sich um 00:00, auch ohne neuen Abruf
        entry.async_on_unload(
            async_track_time_change(
                hass, lambda _now: self.async_update_listeners(), hour=0, minute=0, second=5
            )
        )

    async def _async_update_data(self) -> MensaData:
        try:
            return await self.client.async_get_data(dt_util.now().date())
        except MensaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MensaConnectionError as err:
            raise UpdateFailed(str(err)) from err
