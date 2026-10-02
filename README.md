# Mensa Schule für Home Assistant

Zeigt Guthaben, Speiseplan und Bestellstatus des Schul-Essensportals **WebMenü** (Pöschl Catering, `poeschl-catering.webmenue.info`) in Home Assistant an. Es wird ein Gerät pro Konto angelegt.

> Inoffizielles, privates Projekt ohne Verbindung zu Pöschl Catering oder dem WebMenü-Anbieter. Die Integration meldet sich mit deinen eigenen Zugangsdaten an und **liest nur**: sie bestellt, storniert oder ändert nichts. Bitte beachte die Nutzungsbedingungen des Portals. Nutzung auf eigene Verantwortung. Ändert sich das Seitenlayout, muss der Parser angepasst werden.

## Installation

1. Ordner `custom_components/mensa_schule` nach `/config/custom_components/mensa_schule` kopieren (oder in HACS als benutzerdefiniertes Repository hinzufügen).
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Mensa Schule**.
4. Benutzername und Passwort des WebMenü-Portals eingeben.

Die Daten werden alle 30 Minuten abgerufen: die aktuelle Woche plus so viele Folgewochen, wie für die nächsten 7 Tage nötig sind. Um Mitternacht werden "heute" und "morgen" neu berechnet.

## Entitäten

Die Entitäts-IDs richten sich nach der Sprache deiner Installation, auf Deutsch z. B. `sensor.mensa_schule_guthaben`.

| Entität | Inhalt |
|---|---|
| Guthaben | aktuelles Guthaben in EUR |
| Essen heute / Essen morgen | bestelltes Gericht, sonst "nicht bestellt" oder "kein Angebot" (Attribute: `offer`, `ordered_meals`, `orderable`, `has_offer`) |
| Heute bestellt / Morgen bestellt | Binärsensor, an wenn für den Tag etwas bestellt ist (Attribute `has_offer`, `orderable`, `meals`) |
| Nächste Bestellung | Datum der nächsten bestellten Mahlzeit |
| Nächster unbestellter Tag | nächster Tag mit Angebot, an dem noch bestellt werden kann und noch nichts bestellt ist (Attribut `open_days`) |
| Speiseplan | Zustand = Zahl der Tage mit Angebot in den nächsten 7 Tagen; Attribut `days` mit allen Gerichten, Preisen und Bestellstatus |

"Bestellbar" (`orderable`) bedeutet: Die Bestellfrist des Portals ist für dieses Gericht noch nicht abgelaufen.

## Beispiel: Speiseplan als Dashboard-Karte

```yaml
type: markdown
title: Mensa
content: >
  {% for d in state_attr('sensor.mensa_schule_speiseplan', 'days') or [] %}
  **{{ d.weekday }}, {{ d.date[8:10] }}.{{ d.date[5:7] }}.**
  {% if d.ordered %}✅ {% for m in d.meals if m.ordered %}{{ m.name }}{% endfor %}
  {% else %}⬜ nicht bestellt{% if d.orderable %} (noch bestellbar){% endif %}{% endif %}

  {% else %}
  Kein Speiseplan in den nächsten 7 Tagen
  {% endfor %}
```

## Beispiel: Erinnerung, wenn morgen nichts bestellt ist

```yaml
alias: Mensa Bestellung erinnern
triggers:
  - trigger: time
    at: "18:00:00"
conditions:
  - condition: state
    entity_id: binary_sensor.mensa_schule_morgen_bestellt
    state: "off"
  - condition: template
    value_template: >
      {{ state_attr('binary_sensor.mensa_schule_morgen_bestellt', 'has_offer')
         and state_attr('binary_sensor.mensa_schule_morgen_bestellt', 'orderable') }}
actions:
  - action: notify.notify
    data:
      message: "Mensa: Für morgen ist noch nichts bestellt."
```

## Wenn etwas nicht klappt

- **"Login-Formular nicht lesbar" / "nicht erreichbar":** Das Portal ist nicht erreichbar oder das Formular hat sich geändert.
- **"Keine Daten im Portal erkannt":** Auf der Integrationsseite → drei Punkte → **Diagnose herunterladen**. Die Datei enthält den erkannten Seitentext (ohne Benutzername und Konto-ID) und die geparsten Gerichte.
- Debug-Log in `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.mensa_schule: debug
  ```

## Bekannte Grenzen

- Die Uhrzeit der Bestellfrist wird nicht gelesen, nur ob sie noch offen ist.
- Es gibt kein Bestellen oder Stornieren aus Home Assistant heraus.
- Das Passwort liegt, wie bei allen Integrationen mit Login, im Klartext in `.storage/core.config_entries`.

## Lizenz

[MIT](LICENSE)
