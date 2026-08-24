# haprox connect

![Build](https://github.com/haproxeu/haprox-connect/actions/workflows/build.yml/badge.svg)

Home-Assistant-Add-on, das deine HA-Instanz per WireGuard mit
[haprox.eu](https://haprox.eu) verbindet — danach von überall erreichbar,
ohne dass an deinem Internetanschluss ein Port geöffnet werden muss.

## Installation

1. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store → ⋮ (oben
   rechts) → Repositories**.
2. Diese URL eintragen:
   ```
   https://github.com/haproxeu/haprox-connect
   ```
3. Das Add-on **haprox connect** erscheint im Store — installieren und
   starten.
4. In den Add-on-Einstellungen den Enrollment-Code eintragen, den du vom
   Betreiber bekommen hast, und das Add-on neu starten.

Ausführliche Anleitung, Statusanzeige und Fehlerbehebung:
[haprox_connect/DOCS.md](haprox_connect/DOCS.md).

## Was es tut

- baut einen WireGuard-Tunnel zum Relay auf
- bezieht und erneuert selbstständig ein Let's-Encrypt-Zertifikat für
  deine Adresse — dein privater Schlüssel verlässt die Box nie
- terminiert TLS lokal auf deiner Box
- meldet regelmäßig einen kurzen, anonymisierten Statusbericht über den
  Tunnel ans Relay (Details dazu in `DOCS.md`)

## Verwendete Software

Dieses Add-on baut auf WireGuard, nginx, lego u.a. auf — siehe
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) für die vollständige
Liste inkl. Lizenzen.

## Support

support@haprox.eu
