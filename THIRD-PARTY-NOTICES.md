# Third-Party Notices

Dieses Add-on baut auf öffentlich verfügbarer Drittsoftware auf, die im
veröffentlichten Container-Image enthalten ist oder beim Bauen daraus
eingebettet wird. Diese Liste nennt die wesentlichen Bestandteile und
ihre Lizenzen; sie ersetzt keine Rechtsberatung, ist aber der Stand
unserer eigenen Prüfung (Stand: siehe Git-Historie dieser Datei).

| Komponente | Zweck hier | Lizenz | Projekt |
|---|---|---|---|
| WireGuard / `wireguard-tools` | VPN-Tunnel zum Relay | GPL-2.0 | https://git.zx2c4.com/wireguard-tools |
| nginx | TLS-Terminierung, Weiterleitung an HA Core | BSD-2-Clause | https://nginx.org |
| lego | Let's-Encrypt-Zertifikatsbezug (DNS-01) | MIT | https://github.com/go-acme/lego |
| s6-overlay | Prozess-Supervision (Teil des Basis-Images) | ISC | https://github.com/just-containers/s6-overlay |
| bashio | Supervisor-API-Helfer (Teil des Basis-Images) | MIT | https://github.com/hassio-addons/bashio |
| Alpine Linux (Basis-Image, `jq`, `curl`, `python3` u.a.) | Laufzeitumgebung | überwiegend MIT/BSD | https://alpinelinux.org |

## Was das für uns bedeutet

- Keine dieser Lizenzen ist AGPL — reine Nutzung als separater Prozess
  im Container (kein statisches Verlinken, kein Einbetten fremden
  Quellcodes in unseren eigenen) verlangt von unserem eigenen Code keine
  Lizenzänderung.
- **WireGuard/`wireguard-tools` steht unter GPL-2.0** — der einzige
  Copyleft-Baustein hier. Wir installieren das unveränderte
  Alpine-Paket, ändern nichts am Quellcode; der Quellcode ist über
  Alpines eigene Paketquellen und das verlinkte Upstream-Repository frei
  verfügbar.
- `lego` wird im Dockerfile aus unverändertem, öffentlichem Quellcode
  gebaut (`go install`), kein eigener Fork.
- s6-overlay/bashio kommen bereits fertig im Basis-Image
  `ghcr.io/hassio-addons/base`, das vom Home-Assistant-Community-Projekt
  gepflegt wird — wir bringen sie nicht selbst ein.
