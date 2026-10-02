"""Parser für das WebMenü-Portal (ASP.NET WebForms). Reine Python-Logik ohne Home Assistant.

Jedes Gericht ist eine Karte `li.card.item`. Sie trägt
- Klassen `ordered`/`notordered` und `fristok`/`fristexpired` (Bestellfrist),
- ein Häkchen-Kästchen (angehakt = bestellt),
- das Attribut `data-ntc-billoffare-element` mit Base64-JSON (Datum, Preis,
  QuantityOrdered, Beschreibung, Menügruppe, UserBalance).
Das JSON wird bevorzugt, die sichtbaren Texte dienen als Rückfall.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

AMOUNT_RE = re.compile(r"(?P<sign>[-−–])?\s*(?P<num>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})")
DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
POSTBACK_RE = re.compile(r"__doPostBack\('([^']*)'")
LOGIN_TARGET_FALLBACK = "ctl00$MainContent$btnlogin"


@dataclass
class MealItem:
    """Ein Gericht an einem Tag."""

    day: date
    group: str  # z. B. "Menü 1"
    name: str
    price: float | None = None
    ordered: bool = False
    orderable: bool = False  # Bestellfrist noch offen


@dataclass
class MenuPage:
    """Eine Seite des Speiseplans (eine Woche)."""

    items: list[MealItem] = field(default_factory=list)
    balance: float | None = None
    account: str | None = None
    next_target: str | None = None  # __EVENTTARGET für ">>" (Rückfall)
    fields: dict[str, str] = field(default_factory=dict)  # wie ein Browser abgeschicktes Formular
    date_field: str | None = None  # Name des Datumsfelds (Wochenwahl)
    week_start: date | None = None  # dort eingetragenes Datum


def parse_amount(text: str) -> float | None:
    """'27,25 €' -> 27.25."""
    m = AMOUNT_RE.search(text or "")
    if not m:
        return None
    value = float(m.group("num").replace(".", "").replace(",", "."))
    return -value if m.group("sign") else value


def parse_date(text: str) -> date | None:
    m = DATE_RE.search(text or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def is_login_page(html: str) -> bool:
    return BeautifulSoup(html, "html.parser").select_one("input[type=password]") is not None


def _hidden_fields(form) -> dict[str, str]:
    return {
        i["name"]: i.get("value", "")
        for i in form.select("input[type=hidden][name]")
    }


def _form_fields(form) -> dict[str, str]:
    """Felder so, wie ein Browser sie absenden würde (ohne Passwort, Schaltflächen, deaktivierte)."""
    out: dict[str, str] = {}
    for i in form.select("input[name]"):
        t = (i.get("type") or "text").lower()
        if i.has_attr("disabled") or t in ("password", "button", "submit", "image", "reset", "file"):
            continue
        if t in ("checkbox", "radio"):
            if i.has_attr("checked"):
                out[i["name"]] = i.get("value", "on")
            continue
        out[i["name"]] = i.get("value", "")
    return out


def parse_login_form(html: str, page_url: str) -> tuple[str, dict[str, str], str, str, str]:
    """Rückgabe: (Ziel-URL, versteckte Felder, Feld Benutzer, Feld Passwort, __EVENTTARGET)."""
    soup = BeautifulSoup(html, "html.parser")
    pw = soup.select_one("input[type=password]")
    if pw is None:
        raise ValueError("Kein Passwortfeld gefunden")
    form = pw.find_parent("form")
    if form is None:
        raise ValueError("Passwortfeld liegt in keinem <form>")
    user = form.select_one("input[type=text][name], input[type=email][name]")
    if user is None:
        raise ValueError("Kein Benutzerfeld gefunden")
    target = LOGIN_TARGET_FALLBACK
    for a in form.select("a[href]"):
        m = POSTBACK_RE.search(a["href"])
        if m and "login" in m.group(1).lower():
            target = m.group(1)
            break
    action = urljoin(page_url, form.get("action") or page_url)
    return action, _hidden_fields(form), user["name"], pw["name"], target


def _decode_element(card) -> dict:
    raw = card.get("data-ntc-billoffare-element")
    if not raw:
        return {}
    try:
        return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ")).strip() if node else ""


def _parse_card(card) -> MealItem | None:
    data = _decode_element(card)
    classes = set(card.get("class", []))

    day: date | None = None
    if data.get("BillofFareDate"):
        try:
            day = datetime.fromisoformat(data["BillofFareDate"]).date()
        except ValueError:
            day = None
    if day is None:
        day = parse_date(_text(card.select_one(".billoffaredate .date")))
    if day is None:
        return None

    group = data.get("BillofFareDayGroupDescription") or _text(
        card.select_one(".billoffaredaygroup")
    )
    name = data.get("BillofFareItemDesc") or _text(card.select_one(".billoffaretext"))
    price = data.get("Price")
    if price is None:
        price = parse_amount(_text(card.select_one(".price")))

    checkbox = card.select_one("input[type=checkbox]")
    if "QuantityOrdered" in data:
        ordered = float(data["QuantityOrdered"] or 0) > 0
    elif checkbox is not None:
        ordered = checkbox.has_attr("checked")
    else:
        ordered = "ordered" in classes and "notordered" not in classes

    return MealItem(
        day=day,
        group=group,
        name=name,
        price=float(price) if price is not None else None,
        ordered=ordered,
        orderable="fristok" in classes,
    )


def parse_menu_page(html: str) -> MenuPage:
    """Speiseplan-Seite -> Gerichte, Guthaben, Konto-ID, Ziel der Schaltfläche '>>'."""
    soup = BeautifulSoup(html, "html.parser")
    page = MenuPage()

    for card in soup.select("li.card.item"):
        if item := _parse_card(card):
            page.items.append(item)

    # Guthaben: erst Kopfzeile, sonst JSON einer Karte
    bal = soup.select_one(".user-current-balance")
    page.balance = parse_amount(_text(bal)) if bal else None
    if page.balance is None:
        for card in soup.select("li.card.item"):
            ub = _decode_element(card).get("UserBalance")
            if ub is not None:
                page.balance = float(ub)
                break

    acc = soup.select_one(".wmid .original")
    page.account = _text(acc) or None

    nxt = soup.select_one("a.week-next[href]")
    if nxt and (m := POSTBACK_RE.search(nxt["href"])):
        page.next_target = m.group(1)

    form = soup.select_one("form")
    if form is not None:
        page.fields = _form_fields(form)
    dt = soup.select_one("input.datepicker[name]")
    if dt is not None:
        page.date_field = dt["name"]
        page.week_start = parse_date(dt.get("value", ""))
    return page


def page_summary(html: str) -> list[str]:
    """Für Diagnose: sichtbarer Text ohne Namen-Details (grob)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for sel in (".username", ".wmid", ".orderperson"):
        for el in soup.select(sel):
            el.decompose()
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in soup.get_text("\n").splitlines()]
    return [ln for ln in lines if ln][:200]
