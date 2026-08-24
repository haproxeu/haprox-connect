# Changelog

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
