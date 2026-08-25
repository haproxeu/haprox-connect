# haprox connect

## Was dieses Add-on tut

Verbindet diese Home-Assistant-Instanz über einen WireGuard-Tunnel mit
[haprox.eu](https://haprox.eu). Danach ist Home Assistant unter einer
eigenen Adresse (`https://<zufällige-id>.haprox.eu`) von überall
erreichbar — ohne dass an deinem Internetanschluss ein Port geöffnet
werden muss.

Das Add-on kümmert sich selbstständig um:

- den WireGuard-Tunnel zum Relay
- ein eigenes, kostenloses Zertifikat (Let's Encrypt) für deine Adresse
  — wird von diesem Add-on selbst bezogen und erneuert, dein privater
  Schlüssel verlässt diese Box nie
- die TLS-Verschlüsselung deiner Verbindung
- eine kurze, regelmäßige Statusmeldung an das Relay (siehe unten, was
  genau übertragen wird)

## Einrichtung

1. Add-on installieren und starten.
2. In den Add-on-Einstellungen den Code eintragen, den du vom Betreiber
   bekommen hast (`enrollment_token`, Format `XXXX-XXXX`).
3. Add-on neu starten.

Danach richtet sich alles Weitere von selbst ein. Das kann je nach
Internetverbindung eine Minute dauern — im Log siehst du den Fortschritt
("Baue WireGuard-Tunnel auf...", "Zertifikat ... erfolgreich bezogen").

### Wie du an einen Code kommst

Codes werden vom Betreiber des Relays ausgegeben, nicht vom Add-on
selbst. Ein Code ist **30 Minuten gültig** und **nur einmal verwendbar**.
Läuft er ab oder wurde er schon benutzt, bevor du ihn eintragen konntest:
neuen Code anfordern, siehe "Support" unten.

### Erweiterte Optionen

Normalerweise nicht nötig, nur bei Testumgebungen oder auf Anweisung des
Betreibers ändern:

- `enroll_url` — Adresse des Enrollment-Endpunkts (Standard:
  `https://enroll.haprox.eu`)
- `heartbeat_interval` — Abstand zwischen den Statusmeldungen in Sekunden
  (Standard: 300)

## Was per Heartbeat übertragen wird

Alle `heartbeat_interval` Sekunden meldet sich das Add-on über den
Tunnel (nicht öffentlich) beim Relay mit:

- Add-on- und Home-Assistant-Version (inkl. Betriebssystem-Version)
- Restlaufzeit und letztes Erneuerungsdatum deines Zertifikats
- seit wann der Tunnel steht
- eigene Laufzeit (Uptime)
- ob die interne Weiterleitung an Home Assistant funktioniert
- die letzte Fehlermeldung, falls gerade etwas nicht funktioniert

**Bewusst nicht übertragen:** Namen deiner Geräte/Entitäten,
Geräte-/Integrationslisten, Automationen, Anzahl deiner Benutzer — nichts,
was Rückschlüsse auf das zulässt, was bei dir zuhause läuft. Diese Liste
ist vollständig, es wird nichts darüber hinaus gesammelt.

## Statusanzeige in Home Assistant

Das Add-on legt folgende Entitäten an:

| Entität | Bedeutung |
|---|---|
| `binary_sensor.haprox_tunnel` | Tunnel zum Relay verbunden |
| `binary_sensor.haprox_relay_reachable` | letzte Statusmeldung kam an |
| `sensor.haprox_certificate_days` | Restlaufzeit des Zertifikats in Tagen |
| `sensor.haprox_external_url` | deine externe Adresse |
| `sensor.haprox_status` | `ok`, `cert_error`, `tunnel_down` — oder waehrend der Ersteinrichtung `setting_up_1_5` bis `setting_up_5_5` |

**Während der Ersteinrichtung** (dauert normalerweise ein bis zwei
Minuten) durchläuft `sensor.haprox_status` fünf Stufen: Code wird
geprüft → Verbindung wird aufgebaut → Verbindung steht → Zertifikat
wird bezogen → Bereit. Die Attribute (`step`, `step_total`,
`step_label`) eignen sich für einen Fortschrittsbalken. Bleibt eine
Stufe zu lange stehen, zeigt die Entität `stuck: true` mit einem
Klartext-Hinweis, und du bekommst einmalig eine Benachrichtigung — das
Add-on gibt dabei nicht auf und versucht im Hintergrund weiter (siehe
"Was bei Fehlern zu tun ist" unten für die Ausnahme: ein ungültiger
Code).

Läuft dein Zertifikat in weniger als 20 Tagen ab, erscheint eine
Warnung im Add-on-Log. Unter 7 Tagen zusätzlich eine Benachrichtigung
direkt in Home Assistant.

**Bekannte Einschränkung:** diese Entitäten überleben einen
Neustart von Home Assistant nicht dauerhaft — sie zeigen bis zur
nächsten Statusmeldung "unbekannt" an. Das ist normal, kein Fehler.

## Was bei Fehlern zu tun ist

Zuerst immer ins Add-on-Log schauen — die Meldungen dort sind bewusst
in Klartext gehalten, keine reinen Fehlercodes.

- **"Der Code wurde nicht akzeptiert."** — Code ist abgelaufen (30
  Minuten) oder schon verwendet. Neuen Code anfordern.
- **"Zu viele Versuche in kurzer Zeit."** — mehrfach falsche/abgelaufene
  Codes hintereinander versucht. Kurz warten, dann mit einem gültigen
  Code erneut versuchen.
- **"Relay nicht erreichbar..."** — das Add-on versucht es selbstständig
  immer wieder (mit wachsendem Abstand). Kein Eingreifen nötig, außer
  die Meldung bleibt über Stunden bestehen — dann Internetverbindung
  prüfen oder Support kontaktieren.
- **Warnung zu "Home Assistant Core vertraut diesem Add-on noch nicht
  als Proxy"** — im Log steht der exakt einzufügende Konfigurationsblock
  bzw. der Menüpfad in den HA-Einstellungen. Ohne das schlagen
  Verbindungen über deine `haprox.eu`-Adresse fehl, sobald das
  Zertifikat steht.
- **Enrollment ist mittendrin abgebrochen** (z. B. Stromausfall während
  der Ersteinrichtung) und startet nicht neu: der ursprüngliche Code ist
  in diesem Fall verbraucht, auch wenn die Einrichtung nicht fertig
  wurde. Beim Support um einen **neuen** Code für denselben, bereits
  bestehenden Standort bitten (nicht um einen komplett neuen
  Standort) — deine Adresse bleibt dabei erhalten.

## Wie man sauber wieder aussteigt

1. Add-on deinstallieren (Home Assistant → Einstellungen → Add-ons).
2. Das entfernt den Tunnel und alle lokalen Daten dieses Add-ons
   (`/data`) automatisch.
3. Der Standort bleibt auf dem Relay bestehen, bis er dort aufgeräumt
   wird (das geschieht nicht automatisch und nicht sofort) — falls du
   ihn endgültig entfernt haben möchtest, kurz beim Support Bescheid
   geben.

## Support

**support@haprox.eu**
