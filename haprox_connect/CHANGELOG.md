# Changelog

## 0.4.8

- Echter Bug, live gefunden bei der ersten laengeren Laufzeit auf einer
  echten Instanz: der Heartbeat-eigene `nginx_ok()`-Check oeffnete eine
  nackte TCP-Verbindung zu `wg_ip:443` ohne PROXY-Protocol-Header, den
  unser eigenes nginx (`proxy_protocol on`) aber zwingend erwartet --
  Ergebnis war ein echter `[error] ... broken header while reading
  PROXY protocol`-Eintrag bei **jedem einzelnen Heartbeat**, dauerhaft,
  bei jeder Installation. Sendet jetzt `PROXY UNKNOWN\r\n` (der im
  Standard vorgesehene Weg fuer Healthchecks ohne echte Client-Daten,
  z.B. auch von AWS-Loadbalancern genutzt) -- Fehler verschwindet
  komplett.
- `access_log` fuer die Standort-Domain abgeschaltet -- wurde von
  nichts in diesem Add-on gelesen, wuchs unbegrenzt (inklusive echter
  Besucher-IPs/User-Agents), keine Rotation in diesem minimalen
  Container.

## 0.4.7

- Echter Bug, live gefunden bei der ersten vollstaendigen Installation
  auf einer echten HA-Supervised-Instanz: die Trusted-Proxies-Warnung
  nannte nur `172.30.33.0/24` (das Supervisor-Docker-Netz). Laeuft der
  homeassistant-Container selbst mit Host-Networking (typisch bei
  "Supervised" auf generischem Linux statt echter HAOS), sieht HA Core
  Anfragen von diesem -- ebenfalls host-genetzwerkten -- Add-on aber als
  von `127.0.0.1` kommend, nicht vom Docker-Netz. Die alte Anleitung
  konnte man in diesem Fall beliebig oft richtig eintragen, ohne dass
  sich etwas aenderte. Warnung nennt jetzt beide Adressen
  (`172.30.33.0/24` und `127.0.0.1/32`), schadlos fuer beide
  Netzwerk-Situationen.

## 0.4.6

- Echter Bug, live gefunden bei der ersten vollstaendigen Installation
  auf einer echten HA-Supervised-Instanz: nginx proxyte fest verdrahtet
  auf `127.0.0.1:8123`. Auf dieser Instanz (Supervised auf generischem
  Debian statt HAOS) lief HA Core aber auf Port 80 -- Ergebnis war ein
  echter `502 Bad Gateway` fuer jeden Verbindungsversuch ueber die
  haprox.eu-Adresse, obwohl Tunnel, Zertifikat und Enrollment
  einwandfrei liefen. `nginx/run` fragt den tatsaechlichen Port jetzt
  vorher bei der Supervisor-API ab (`/core/info`), Fallback 8123 nur
  falls diese Abfrage selbst fehlschlaegt.

## 0.4.5

- WireGuard-Interface heisst jetzt `wghaprox` statt `wg0`. Grund: das
  Add-on laeuft mit `host_network: true`, das Interface entsteht also im
  Netzwerk-Namespace des Hosts, nicht in einem eigenen Docker-Netz.
  `wg0` ist die mit Abstand haeufigste Standardbezeichnung fuer
  WireGuard-Interfaces (auch im offiziellen HA-WireGuard-Add-on) --
  wer auf seiner Box schon ein anderes WireGuard laufen hat oder die
  Instanz selbst als WireGuard-Server betreibt, haette damit ein reales
  Namenskollisionsrisiko gehabt.

## 0.4.4

- Echter Bug, live gefunden: `services.d`-Dienste starten ohne
  garantierte Reihenfolge. War das Zertifikat schon vorhanden (jeder
  Neustart nach dem ersten Erfolg), versuchte `nginx` teils schneller
  an `wg_ip:443` zu binden, als `wireguard/run` das Interface
  hochgefahren hatte (`bind() to <wg_ip>:443 failed: Address not
  available`) — bisher nur durch s6s automatischen Neustart kaschiert,
  kein verlässliches Verhalten. `nginx/run` wartet jetzt zusätzlich
  aktiv, bis die Adresse wirklich auf `wg0` sitzt, bevor gerendert und
  gestartet wird.

## 0.4.3

- Wichtiger echter Bug, live gefunden: Alpines nginx-Paket bringt eine
  `http.d/default.conf` mit, die `0.0.0.0:80` belegt. Wegen
  `host_network: true` ist das der **Host**-Port -- auf der Test-VM
  stellte sich heraus, dass Port 80 dort bereits von Home Assistant
  Core selbst belegt ist, unsere Stock-`default.conf` kollidierte
  direkt damit (`bind() to 0.0.0.0:80 failed: Address in use`,
  Nginx-Dienst startete in einer Schleife). Wir brauchen Port 80 nie
  (nur `wg_ip:443`) -- die mitgelieferte `default.conf` wird jetzt im
  Dockerfile entfernt.

## 0.4.2

- Echter Bug, gefunden im selben Testlauf: `heartbeat.py` schickte
  `ha_os_version: null`, sobald die Supervisor-API dafür kein Feld
  liefert (z. B. auf "Home Assistant Supervised" auf generischem Debian
  statt echtem HAOS — genau die Umgebung, in der getestet wurde) — das
  Response-Schema (`str`, nicht `str | None`) lehnte den Heartbeat
  daraufhin mit `422 Unprocessable Entity` ab. `fetch_ha_version()`/
  `fetch_addon_version()`/`fetch_ha_os_version()` fangen ein `null`-Feld
  jetzt selbst ab (`or ""`), nicht nur einen fehlgeschlagenen Request.

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
  Support-Kontakt).

## 0.3.0

- Heartbeat und Statusentitäten: `heartbeat.py` meldet sich periodisch
  beim Relay (`http://`, Tunnel ist die Transportsicherheit) und setzt
  fünf Statusentitäten über die Supervisor-API
  (`binary_sensor.haprox_tunnel`, `binary_sensor.haprox_relay_reachable`,
  `sensor.haprox_certificate_days`, `sensor.haprox_external_url`,
  `sensor.haprox_status`), inklusive persistenter Benachrichtigung ab
  7 Tagen Zertifikats-Restlaufzeit. `sensor.haprox_traffic_month` noch
  nicht gesetzt. Gemeinsame Supervisor-/Logging-Helfer nach
  `haprox_common.py` ausgelagert.

## 0.2.0

- Zertifikat und nginx: `lego --dns acme-dns` bezieht das Standort-
  Zertifikat nach Tunnelaufbau (Backoff, nie aufgeben), Erneuerung
  ARI-gesteuert alle 12h geprüft. nginx terminiert TLS auf der
  Tunnel-IP, Weiterleitung an HA Core, mit empirischem Trusted-Proxies-
  Check (kein `configuration.yaml`-Parsing). Noch kein Heartbeat, keine
  Statusentitäten, keine 20/7-Tage-Ablaufwarnung.

## 0.1.0

- Add-on-Gerüst: Enrollment gegen `enroll.haprox.eu`, atomare
  Zustandshaltung unter `/data/haprox.json`, WireGuard-Tunnelaufbau.
  Noch kein Zertifikatsbezug, keine nginx-Terminierung, kein Heartbeat.
