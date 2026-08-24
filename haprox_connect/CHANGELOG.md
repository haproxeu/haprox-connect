# Changelog

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
