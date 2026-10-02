"""HTTP-Client für das WebMenü-Portal (Login per ASP.NET-Formular, danach nur Lesen)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import aiohttp

from .const import BASE_URL, HORIZON_DAYS, LOGIN_URL, MAX_EXTRA_PAGES, MENU_URL
from .parser import (
    MealItem,
    MenuPage,
    is_login_page,
    page_summary,
    parse_login_form,
    parse_menu_page,
)

_LOGGER = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=45)


class MensaError(Exception):
    """Basisklasse."""


class MensaAuthError(MensaError):
    """Zugangsdaten falsch."""


class MensaConnectionError(MensaError):
    """Server nicht erreichbar oder unerwartete Antwort."""


@dataclass
class MensaData:
    """Alles, was die Sensoren brauchen."""

    balance: float | None = None
    account: str | None = None
    items: list[MealItem] = field(default_factory=list)

    def days(self) -> dict[date, list[MealItem]]:
        out: dict[date, list[MealItem]] = {}
        for it in sorted(self.items, key=lambda i: (i.day, i.group)):
            out.setdefault(it.day, []).append(it)
        return out


class MensaClient:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self.last_lines: list[str] = []

    async def async_login(self) -> None:
        try:
            async with self._session.get(LOGIN_URL, timeout=TIMEOUT) as resp:
                html = await resp.text()
                page_url = str(resp.url)
            if not is_login_page(html):
                return  # Sitzung noch gültig
            try:
                action, hidden, user_f, pw_f, target = parse_login_form(html, page_url)
            except ValueError as err:
                raise MensaConnectionError(f"Login-Formular nicht lesbar: {err}") from err
            payload = {
                **hidden,
                "__EVENTTARGET": target,
                "__EVENTARGUMENT": "",
                user_f: self._username,
                pw_f: self._password,
            }
            async with self._session.post(
                action,
                data=payload,
                headers={"Referer": page_url, "Origin": BASE_URL},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status >= 400:
                    raise MensaConnectionError(f"Login-Antwort HTTP {resp.status}")
                result = await resp.text()
            if is_login_page(result):
                raise MensaAuthError("Anmeldung fehlgeschlagen")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MensaConnectionError(str(err)) from err

    async def _get_menu(self) -> str:
        async with self._session.get(MENU_URL, timeout=TIMEOUT) as resp:
            if resp.status >= 500:
                raise MensaConnectionError(f"Serverfehler {resp.status}")
            return await resp.text()

    async def _post_menu(self, payload: dict[str, str]) -> str:
        async with self._session.post(
            MENU_URL,
            data=payload,
            headers={"Referer": MENU_URL, "Origin": BASE_URL},
            timeout=TIMEOUT,
        ) as resp:
            if resp.status >= 500:
                raise MensaConnectionError(f"Serverfehler {resp.status}")
            return await resp.text()

    async def async_get_data(self, today: date) -> MensaData:
        """Aktuelle Woche lesen und die Folgewochen per Datumsauswahl holen, bis HORIZON_DAYS abgedeckt sind."""
        try:
            html = await self._get_menu()
            if is_login_page(html):
                _LOGGER.debug("Sitzung abgelaufen, melde neu an")
                await self.async_login()
                html = await self._get_menu()
                if is_login_page(html):
                    raise MensaAuthError("Speiseplan nach Login nicht erreichbar")

            self.last_lines = page_summary(html)
            pages = [parse_menu_page(html)]
            horizon = today + timedelta(days=HORIZON_DAYS - 1)

            # Wochen gezielt per Datumsauswahl holen (">>" springt nicht verlässlich 1 Woche)
            first = pages[0]
            week = first.week_start or (today - timedelta(days=today.weekday()))
            for _ in range(MAX_EXTRA_PAGES):
                week += timedelta(days=7)
                if week > horizon:
                    break
                last = pages[-1]
                payload = dict(last.fields)
                payload["__EVENTARGUMENT"] = ""
                if last.date_field:
                    payload[last.date_field] = week.strftime("%d.%m.%Y")
                    payload["__EVENTTARGET"] = last.date_field
                elif last.next_target:
                    payload["__EVENTTARGET"] = last.next_target
                else:
                    break
                html = await self._post_menu(payload)
                if is_login_page(html):
                    raise MensaConnectionError("Sitzung beim Blättern verloren")
                pages.append(parse_menu_page(html))
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MensaConnectionError(str(err)) from err

        if first.balance is None and not any(p.items for p in pages):
            raise MensaConnectionError(
                "Keine Daten im Portal erkannt (Layout geändert?). "
                "Der Diagnose-Download der Integration enthält den Seitentext."
            )
        items: dict[tuple, MealItem] = {}
        for p in pages:
            for it in p.items:
                items[(it.day, it.group, it.name)] = it
        data = MensaData(balance=first.balance, account=first.account, items=list(items.values()))
        _LOGGER.debug(
            "Gelesen: Guthaben=%s, %d Gerichte an %d Tagen (%d Seiten)",
            data.balance,
            len(data.items),
            len(data.days()),
            len(pages),
        )
        return data
