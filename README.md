# haprox-connect

Home-Assistant-Add-on, das eine HA-Instanz per WireGuard mit
[haprox.eu](https://haprox.eu) verbindet (Selbstregistrierung per
Enrollment-Code, siehe `addon.md` im Relay-Repo `/root/haprox`).

**Stand:** Gerüst (`addon.md` Abschnitt 11, Schritt 2 von 6) —
Enrollment, Zustandshaltung, WireGuard-Tunnelaufbau. Noch kein
Zertifikatsbezug/nginx im Add-on (Schritt 3), kein Heartbeat/keine
Statusentitäten (Schritt 4), Fehlerfälle noch nicht gezielt durchgespielt
(Schritt 5), kein echter Multi-Arch-Build/Veröffentlichung (Schritt 6).

**Noch nicht getestet:** echter Container-Build, echte Supervisor-API,
echter Tunnelaufbau von einer realen HA-Box — das Relay (`/root/haprox`)
hat kein Docker. Nur die Enrollment-HTTP-Logik wurde gegen den echten
`enroll.haprox.eu`-Endpunkt verifiziert. Siehe `STATUS.md` im
Relay-Repo für den vollständigen Stand.

Vollständige `DOCS.md` (für Kunden) folgt in Schritt 6.
