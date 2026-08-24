# haprox-connect

Home-Assistant-Add-on, das eine HA-Instanz per WireGuard mit
[haprox.eu](https://haprox.eu) verbindet (Selbstregistrierung per
Enrollment-Code, siehe `addon.md` im Relay-Repo `/root/haprox`).

**Stand:** Enrollment, Zustandshaltung, WireGuard-Tunnelaufbau,
Zertifikatsbezug (`lego --dns acme-dns`), nginx-TLS-Terminierung,
Heartbeat und Statusentitäten (`addon.md` Abschnitt 11, Schritt 4 von 6).
`sensor.haprox_traffic_month` noch nicht gesetzt (Datenquelle
verschoben). Fehlerfälle noch nicht gezielt durchgespielt (Schritt 5),
kein echter Multi-Arch-Build/Veröffentlichung (Schritt 6).

**Noch nicht getestet:** echter Container-Build (Multi-Stage inkl.
Go-Cross-Compile), echte Supervisor-API, echter Tunnelaufbau/
Zertifikatsbezug/nginx-Start im Zusammenspiel auf einer realen HA-Box —
das Relay (`/root/haprox`) hat kein Docker. Enrollment- und
Zertifikats-HTTP-Logik wurden aber beide einzeln gegen die echten
`enroll.haprox.eu`/`acme-dns`-Endpunkte verifiziert (von diesem VPS
aus, das ja selbst der Tunnel-Endpunkt ist). Siehe `STATUS.md` im
Relay-Repo für den vollständigen Stand.

Vollständige `DOCS.md` (für Kunden) folgt in Schritt 6.
