"""Sensoren: Guthaben, Essen heute/morgen, nächste Bestellung, nächster offener Tag, Speiseplan."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MensaConfigEntry
from .const import CURRENCY, HORIZON_DAYS
from .entity import (
    MensaEntity,
    day_dict,
    meal_dict,
    offers,
    ordered,
    upcoming_days,
)

TEXT = {
    "de": {"none": "kein Angebot", "open": "nicht bestellt"},
    "en": {"none": "no offer", "open": "not ordered"},
}


async def async_setup_entry(
    hass: HomeAssistant, entry: MensaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities(
        [
            MensaBalance(c),
            MensaMealDay(c, "today", 0),
            MensaMealDay(c, "tomorrow", 1),
            MensaNextOrder(c),
            MensaNextOpenDay(c),
            MensaMenu(c),
        ]
    )


class MensaBalance(MensaEntity, SensorEntity):
    _attr_translation_key = "balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "balance")

    @property
    def native_value(self) -> float | None:
        return self.data.balance


class MensaMealDay(MensaEntity, SensorEntity):
    """Bestelltes Essen für heute/morgen, sonst 'nicht bestellt' oder 'kein Angebot'."""

    def __init__(self, coordinator, kind: str, offset: int) -> None:
        super().__init__(coordinator, f"meal_{kind}")
        self._attr_translation_key = f"meal_{kind}"
        self._offset = offset

    @property
    def _day(self) -> date:
        return self.today + timedelta(days=self._offset)

    @property
    def native_value(self) -> str:
        texts = TEXT["de" if self.language.startswith("de") else "en"]
        got = ordered(self.data, self._day)
        if got:
            return " + ".join(i.name for i in got)
        return texts["open"] if offers(self.data, self._day) else texts["none"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        got = ordered(self.data, self._day)
        items = offers(self.data, self._day)
        return {
            "date": self._day.isoformat(),
            "has_offer": bool(items),
            "is_ordered": bool(got),
            "orderable": any(i.orderable for i in items),
            "ordered_meals": [meal_dict(i) for i in got],
            "offer": [meal_dict(i) for i in items],
        }


class MensaNextOrder(MensaEntity, SensorEntity):
    """Datum der nächsten bestellten Mahlzeit (ab heute)."""

    _attr_translation_key = "next_order"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "next_order")

    def _next(self) -> date | None:
        days = sorted({i.day for i in self.data.items if i.ordered and i.day >= self.today})
        return days[0] if days else None

    @property
    def native_value(self) -> date | None:
        return self._next()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self._next()
        return {"meals": [meal_dict(i) for i in ordered(self.data, d)]} if d else None


class MensaNextOpenDay(MensaEntity, SensorEntity):
    """Nächster Tag mit Angebot, an dem noch bestellt werden kann und noch nichts bestellt ist."""

    _attr_translation_key = "next_open_day"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "next_open_day")

    def _open_days(self) -> list[date]:
        by_day: dict[date, list] = {}
        for i in self.data.items:
            if i.day >= self.today:
                by_day.setdefault(i.day, []).append(i)
        return sorted(
            d
            for d, items in by_day.items()
            if any(i.orderable for i in items) and not any(i.ordered for i in items)
        )

    @property
    def native_value(self) -> date | None:
        days = self._open_days()
        return days[0] if days else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        days = self._open_days()
        return {"open_days": [d.isoformat() for d in days], "count": len(days)}


class MensaMenu(MensaEntity, SensorEntity):
    """Speiseplan der nächsten 7 Tage. Zustand = Anzahl Tage mit Angebot, Details im Attribut."""

    _attr_translation_key = "menu"
    _attr_native_unit_of_measurement = "d"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "menu")

    @property
    def native_value(self) -> int:
        return len(upcoming_days(self.data, self.today))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        days = upcoming_days(self.data, self.today)
        return {
            "horizon_days": HORIZON_DAYS,
            "days": [day_dict(self.data, d, self.language) for d in days],
        }
