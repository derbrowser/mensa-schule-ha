"""Konstanten der Mensa-Schule-Integration (WebMenü von Pöschl Catering)."""

from datetime import timedelta

DOMAIN = "mensa_schule"
BASE_URL = "https://poeschl-catering.webmenue.info"
LOGIN_URL = f"{BASE_URL}/Login.aspx"
MENU_URL = f"{BASE_URL}/BillofFare.aspx"
SCAN_INTERVAL = timedelta(hours=1)
HORIZON_DAYS = 7  # Zeitfenster des Sensors "Speiseplan" (ab heute)
MAX_EXTRA_PAGES = 3  # so viele zusätzliche Wochenseiten werden pro Abruf höchstens geladen
NEXT_WEEK_FROM_WEEKDAY = 5  # ab diesem Wochentag (0 = Montag, 5 = Samstag) wird statt der aktuellen die Folgewoche geholt
CURRENCY = "EUR"
