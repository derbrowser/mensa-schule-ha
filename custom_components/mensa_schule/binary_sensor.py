"""Binärsensoren: Für heute/morgen ist etwas bestellt."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MensaConfigEntry
from .entity import MensaEntity, meal_dict, offers, ordered


async def async_setup_entry(
    hass: HomeAssistant, entry: MensaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities([MensaOrdered(c, "today", 0), MensaOrdered(c, "tomorrow", 1)])


class MensaOrdered(MensaEntity, BinarySensorEntity):
    def __init__(self, coordinator, kind: str, offset: int) -> None:
        super().__init__(coordinator, f"ordered_{kind}")
        self._attr_translation_key = f"ordered_{kind}"
        self._offset = offset

    @property
    def _day(self):
        return self.today + timedelta(days=self._offset)

    @property
    def is_on(self) -> bool:
        return bool(ordered(self.data, self._day))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = offers(self.data, self._day)
        return {
            "date": self._day.isoformat(),
            "has_offer": bool(items),
            "orderable": any(i.orderable for i in items),
            "meals": [meal_dict(i) for i in ordered(self.data, self._day)],
        }
