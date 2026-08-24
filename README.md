# haprox-connect

Home-Assistant-Add-on, das eine HA-Instanz per WireGuard mit
[haprox.eu](https://haprox.eu) verbindet (Selbstregistrierung per
Enrollment-Code, siehe `addon.md` im Relay-Repo `/root/haprox`).

**Stand:** `addon.md` Abschnitt 11 ist funktional vollständig umgesetzt
(Schritt 1–5: Enrollment, Zustandshaltung, WireGuard, Zertifikatsbezug
via `lego --dns acme-dns`, nginx-TLS-Terminierung, Heartbeat +
Statusentitäten, Standort-Reset, verwaiste-Standorte-Erkennung). Schritt
6 (Repository/Pipeline/Doku) ist lokal vorbereitet: `.github/workflows/
build.yml` (Multi-Arch-Build + monatlicher Pflicht-Rebuild), `DOCS.md`
(Kundendokumentation). **Noch offen, bevor das real funktioniert:**

- `ghcr.io/SET-ME/...` (`config.yaml: image`) und
  `github.com/SET-ME/...` (`config.yaml`/`repository.yaml: url`) sind
  Platzhalter — durch den echten GitHub-Benutzernamen/Orga ersetzen.
- Repository muss real auf GitHub existieren, damit der Workflow
  überhaupt laufen kann — bewusst noch nicht automatisch angelegt/
  gepusht (Rücksprache mit dem Nutzer, siehe `STATUS.md` im Relay-Repo).
- `support@haprox.eu` (in `DOCS.md`) muss als Postfach/Alias im
  bestehenden Migadu-Setup noch angelegt werden.

`sensor.haprox_traffic_month` bewusst nicht gesetzt (Datenquelle
— relay-seitige Traffic-Historie — auf später verschoben).

**Noch nicht getestet:** echter Container-Build (Multi-Stage inkl.
Go-Cross-Compile), echte Supervisor-API, echter Tunnelaufbau/
Zertifikatsbezug/nginx-Start im Zusammenspiel auf einer realen HA-Box,
der CI-Workflow selbst — das Relay (`/root/haprox`) hat kein Docker und
es existiert noch kein echtes GitHub-Repository. Enrollment-, Zertifikats-
und Heartbeat-HTTP-Logik (inkl. Standort-Reset) wurden aber jeweils
einzeln gegen die echten `enroll.haprox.eu`/`acme-dns`/Heartbeat-
Endpunkte verifiziert (von diesem VPS aus, das ja selbst der
Tunnel-Endpunkt ist). Siehe `STATUS.md` im Relay-Repo für den
vollständigen Stand.
