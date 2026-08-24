# Changelog

## 0.4.1

- Echter Bug, gefunden beim ersten Test auf echtem Home Assistant
  Supervised: `services.d/wireguard/run` nutzte `pause`, um den Dienst
  nach dem Tunnelaufbau am Leben zu halten — existiert im
  `hassio-addons/base`-Image nicht (`exec: pause: not found`), der
  Dienst lief dadurch in einer Sekundentakt-Neustartschleife. Auf
  `sleep infinity` gewechselt.

## 0.4.0

- Repository und Auslieferung: `.github/workflows/build.yml` baut
  Multi-Arch-Images (aarch64, amd64) und schiebt sie nach GHCR, inkl.
  Pflicht-Rebuild am 1. jedes Monats (Sicherheitsupdates der
  Basis-Images, auch ohne Codeänderung). `config.yaml` zieht jetzt das
  von der CI gebaute Image (`image:`-Feld) statt lokal auf der Box zu
  bauen. Vollständige `DOCS.md` für Kunden (Funktionsweise, Heartbeat-
  Inhalt, Fehlerbehebung inkl. Standort-Reset, sauberer Ausstieg,
  Support-Kontakt). **`ghcr.io/SET-ME/...` und `github.com/SET-ME/...`
  sind noch Platzhalter** — durch den echten GitHub-Benutzernamen/Orga
  ersetzen, sobald das Repository existiert (siehe `STATUS.md` im
  Relay-Repo). (`addon.md` Abschnitt 11, Schritt 6 von 6 — letzter
  Schritt.)

## 0.3.0

- Heartbeat und Statusentitäten: `heartbeat.py` meldet sich periodisch
  beim Relay (`http://`, Tunnel ist die Transportsicherheit) und setzt
  fünf Statusentitäten über die Supervisor-API
  (`binary_sensor.haprox_tunnel`, `binary_sensor.haprox_relay_reachable`,
  `sensor.haprox_certificate_days`, `sensor.haprox_external_url`,
  `sensor.haprox_status`), inklusive persistenter Benachrichtigung ab
  7 Tagen Zertifikats-Restlaufzeit. `sensor.haprox_traffic_month` noch
  nicht gesetzt (Datenquelle verschoben, siehe `STATUS.md` im
  Relay-Repo). Gemeinsame Supervisor-/Logging-Helfer nach
  `haprox_common.py` ausgelagert. (`addon.md` Abschnitt 11, Schritt 4
  von 6.)

## 0.2.0

- Zertifikat und nginx: `lego --dns acme-dns` bezieht das Standort-
  Zertifikat nach Tunnelaufbau (Backoff, nie aufgeben), Erneuerung
  ARI-gesteuert alle 12h geprüft. nginx terminiert TLS auf der
  Tunnel-IP, Weiterleitung an HA Core, mit empirischem Trusted-Proxies-
  Check (kein `configuration.yaml`-Parsing). Noch kein Heartbeat, keine
  Statusentitäten, keine 20/7-Tage-Ablaufwarnung (siehe `addon.md`
  Abschnitt 11, Schritt 3 von 6).

## 0.1.0

- Add-on-Gerüst: Enrollment gegen `enroll.haprox.eu`, atomare
  Zustandshaltung unter `/data/haprox.json`, WireGuard-Tunnelaufbau.
  Noch kein Zertifikatsbezug, keine nginx-Terminierung, kein Heartbeat
  (siehe `addon.md` Abschnitt 11, Schritt 2 von 6).
