"""Konstanten der Mensa-Schule-Integration (WebMenü von Pöschl Catering)."""

from datetime import timedelta

DOMAIN = "mensa_schule"
BASE_URL = "https://poeschl-catering.webmenue.info"
LOGIN_URL = f"{BASE_URL}/Login.aspx"
MENU_URL = f"{BASE_URL}/BillofFare.aspx"
SCAN_INTERVAL = timedelta(hours=1)
HORIZON_DAYS = 7  # so viele Tage (ab heute) soll der Speiseplan abdecken
MAX_EXTRA_PAGES = 3  # so oft wird maximal auf ">>" (nächste Woche) geklickt
CURRENCY = "EUR"
