"""Basis-Entität und Hilfsfunktionen (ein Gerät pro Konto)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import MensaData
from .const import DOMAIN, HORIZON_DAYS, MENU_URL
from .coordinator import MensaCoordinator
from .parser import MealItem

WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def offers(data: MensaData, day: date) -> list[MealItem]:
    return [i for i in data.items if i.day == day]


def ordered(data: MensaData, day: date) -> list[MealItem]:
    return [i for i in offers(data, day) if i.ordered]


def meal_dict(i: MealItem) -> dict[str, Any]:
    return {"group": i.group, "name": i.name, "price": i.price}


def day_dict(data: MensaData, day: date, language: str) -> dict[str, Any]:
    names = WEEKDAYS_DE if language.startswith("de") else WEEKDAYS_EN
    items = offers(data, day)
    return {
        "date": day.isoformat(),
        "weekday": names[day.weekday()],
        "orderable": any(i.orderable for i in items),
        "ordered": any(i.ordered for i in items),
        "meals": [{**meal_dict(i), "ordered": i.ordered, "orderable": i.orderable} for i in items],
    }


def upcoming_days(data: MensaData, today: date, n: int = HORIZON_DAYS) -> list[date]:
    """Tage mit Angebot in den nächsten n Tagen (heute eingeschlossen)."""
    end = today + timedelta(days=n - 1)
    return sorted({i.day for i in data.items if today <= i.day <= end})


class MensaEntity(CoordinatorEntity[MensaCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: MensaCoordinator, kind: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{kind}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Mensa Schule",
            manufacturer="Pöschl Catering (WebMenü)",
            configuration_url=MENU_URL,
        )

    @property
    def data(self) -> MensaData:
        return self.coordinator.data

    @property
    def today(self) -> date:
        return dt_util.now().date()

    @property
    def language(self) -> str:
        return self.hass.config.language if self.hass else "de"
