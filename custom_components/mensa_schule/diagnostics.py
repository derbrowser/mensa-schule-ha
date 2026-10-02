"""Diagnose-Download (Zugangsdaten und Namen werden entfernt)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import MensaConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MensaConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), {CONF_USERNAME, CONF_PASSWORD}),
        "balance": data.balance if data else None,
        "items": [
            {**asdict(i), "day": i.day.isoformat()} for i in (data.items if data else [])
        ],
        # Sichtbarer Seitentext (ohne Benutzername/Konto-ID), um den Parser anzupassen
        "page_lines": coordinator.client.last_lines,
    }
