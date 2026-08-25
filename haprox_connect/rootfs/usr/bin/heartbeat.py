#!/usr/bin/env python3
"""Heartbeat + Statusentitaeten fuer haprox-connect.

Laeuft als s6-Longrun-Dienst (etc/services.d/heartbeat/run), meldet sich
alle heartbeat_interval Sekunden beim Relay und setzt danach die
Statusentitaeten ueber die Supervisor-API -- unabhaengig davon, ob der
Heartbeat selbst ankam (die Entitaeten spiegeln den lokal bekannten
Zustand, nicht eine Bestaetigung vom Relay).

sensor.haprox_traffic_month wird bewusst NICHT gesetzt -- die
Datenquelle (Relay-seitige Traffic-Historie) ist auf spaeter verschoben.
sensor.haprox_status zeigt waehrend der Ersteinrichtung "setting_up_X_5"
(siehe run_setup_progress()), danach dauerhaft "ok"/"cert_error"/"tunnel_down".
"pending_activation" bleibt weiterhin unimplementiert -- braucht einen
Verwaltungszustand vom Relay, den der Heartbeat-Endpunkt aktuell nicht
zurueckgibt.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import haprox_common
from haprox_common import load_state, log, supervisor_request

OPTIONS_PATH = Path(os.environ.get("HAPROX_OPTIONS_PATH", "/data/options.json"))
LEGO_PATH = Path(os.environ.get("HAPROX_LEGO_PATH", "/data/lego"))
TUNNEL_ESTABLISHED_PATH = Path(
    os.environ.get("HAPROX_TUNNEL_ESTABLISHED_PATH", "/data/tunnel_established")
)
LAST_ERROR_PATH = Path(os.environ.get("HAPROX_LAST_ERROR_PATH", "/data/last_error"))

CERT_WARN_DAYS = 20
CERT_CRITICAL_DAYS = 7
DEFAULT_HEARTBEAT_INTERVAL = 300

_start_monotonic = time.monotonic()


def load_options() -> dict:
    return json.loads(OPTIONS_PATH.read_text())


def cert_expires(domain: str) -> str | None:
    cert_file = LEGO_PATH / "certificates" / f"{domain}.crt"
    if not cert_file.exists():
        return None
    result = subprocess.run(
        ["openssl", "x509", "-in", str(cert_file), "-noout", "-enddate"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    raw = result.stdout.strip().removeprefix("notAfter=").removesuffix(" GMT")
    dt = datetime.strptime(raw, "%b %d %H:%M:%S %Y")
    return dt.replace(tzinfo=timezone.utc).isoformat()


def cert_last_renewal(domain: str) -> str | None:
    cert_file = LEGO_PATH / "certificates" / f"{domain}.crt"
    if not cert_file.exists():
        return None
    return datetime.fromtimestamp(cert_file.stat().st_mtime, tz=timezone.utc).isoformat()


def tunnel_established() -> str | None:
    if TUNNEL_ESTABLISHED_PATH.exists():
        return TUNNEL_ESTABLISHED_PATH.read_text().strip()
    return None


def tunnel_up() -> bool:
    """wghaprox-Handshake juenger als 5 Minuten (grosszuegig gegenueber
    PersistentKeepalive=25, toleriert kurze Aussetzer ohne sofort
    'tunnel_down' zu melden)."""
    result = subprocess.run(
        ["wg", "show", "wghaprox", "latest-handshakes"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return False
    parts = result.stdout.strip().split("\t")
    if len(parts) < 2:
        return False
    latest = int(parts[1])
    return latest > 0 and (time.time() - latest) < 300


def tunnel_up_once() -> bool:
    """Wie tunnel_up(), aber ohne die 5-Minuten-Frische-Grenze -- reiner
    'gab es je einen Handshake'-Check fuer Setup-Stufe 3 (ein einmaliges
    Ereignis, kein wiederkehrender Frische-Status wie im Normalbetrieb)."""
    result = subprocess.run(
        ["wg", "show", "wghaprox", "latest-handshakes"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return False
    parts = result.stdout.strip().split("\t")
    if len(parts) < 2:
        return False
    return int(parts[1]) > 0


def _fetch_ha_core_port() -> int:
    """Wie der Bash-Fix in services.d/nginx/run -- HA Core kann auf einem
    anderen Port als 8123 laufen (z.B. Supervised auf generischem Linux),
    /core/info kennt den tatsaechlichen Wert."""
    try:
        port = supervisor_request("GET", "/core/info")["data"]["port"]
        return int(port) if port else 8123
    except Exception:
        return 8123


def _local_core_reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return True
    except OSError:
        return False


def nginx_ok(wg_ip: str) -> bool:
    """Echter Bug, live gefunden: eine nackte TCP-Verbindung ohne PROXY-
    Protocol-Header liess unser eigenes nginx (`proxy_protocol on`) bei
    jedem Heartbeat einen echten Fehler loggen ("broken header while
    reading PROXY protocol") -- alle heartbeat_interval Sekunden, dauerhaft.
    "PROXY UNKNOWN\\r\\n" ist der im Standard vorgesehene Weg, einen
    Healthcheck ohne echte Client-Daten anzukuendigen (nutzen z.B. auch
    AWS-Loadbalancer dafuer), nginx akzeptiert das ohne Fehlermeldung."""
    try:
        with socket.create_connection((wg_ip, 443), timeout=3) as sock:
            sock.sendall(b"PROXY UNKNOWN\r\n")
            return True
    except OSError:
        return False


def last_error() -> str | None:
    if LAST_ERROR_PATH.exists():
        text = LAST_ERROR_PATH.read_text().strip()
        return text or None
    return None


def fetch_ha_version() -> str:
    try:
        # `or ""`: das Feld selbst kann null sein (nicht nur der Request
        # fehlschlagen) -- das Relay erwartet hier einen str, kein
        # str|None (echter Bug beim ersten Test auf echtem Supervised
        # gefunden: /os/info liefert dort null, da kein echtes HAOS).
        return supervisor_request("GET", "/core/info")["data"]["version"] or ""
    except Exception:
        return ""


def fetch_addon_version() -> str:
    try:
        return supervisor_request("GET", "/addons/self/info")["data"]["version"] or ""
    except Exception:
        return ""


def fetch_ha_os_version() -> str:
    try:
        return supervisor_request("GET", "/os/info")["data"]["version"] or ""
    except Exception:
        return ""


def gather_payload(state: dict) -> dict:
    domain = state["domain"]
    return {
        "site_id": state["site_id"],
        "addon_version": fetch_addon_version(),
        "ha_version": fetch_ha_version(),
        "ha_os_version": fetch_ha_os_version(),
        "cert_expires": cert_expires(domain),
        "cert_last_renewal": cert_last_renewal(domain),
        "tunnel_established": tunnel_established(),
        "addon_uptime_seconds": int(time.monotonic() - _start_monotonic),
        "nginx_ok": nginx_ok(state["wg_ip"]),
        "last_error": last_error(),
    }


def send_heartbeat(state: dict, payload: dict) -> bool:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        state["heartbeat_url"], data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {state['heartbeat_secret']}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, OSError) as exc:
        log("heartbeat", f"Heartbeat fehlgeschlagen: {exc}")
        return False


def set_entity(entity_id: str, state_value: str, attributes: dict | None = None) -> None:
    haprox_common.set_entity("heartbeat", entity_id, state_value, attributes)


def compute_status(tunnel_ok: bool, cert_days: int | None, has_error: bool) -> str:
    if not tunnel_ok:
        return "tunnel_down"
    if cert_days is None or has_error:
        return "cert_error"
    return "ok"


def notify_cert_expiry(domain: str, cert_days: int) -> None:
    """Ab 7 Tagen Restlaufzeit zusaetzlich zur Log-Warnung eine
    persistente Benachrichtigung in Home Assistant."""
    if cert_days >= CERT_CRITICAL_DAYS:
        return
    haprox_common.notify(
        "haprox_connect_cert_expiry",
        "haprox-connect: Zertifikat läuft bald ab",
        f"Das Zertifikat für {domain} läuft in {cert_days} Tagen ab "
        "und wurde noch nicht erneuert. Bitte die Add-on-Logs prüfen.",
        "heartbeat",
    )


def update_entities(state: dict, payload: dict, heartbeat_ok: bool) -> None:
    tunnel_ok = tunnel_up()
    cert_days = None
    if payload["cert_expires"]:
        expires = datetime.fromisoformat(payload["cert_expires"])
        cert_days = (expires - datetime.now(timezone.utc)).days

    set_entity("binary_sensor.haprox_tunnel", "on" if tunnel_ok else "off")
    set_entity("binary_sensor.haprox_relay_reachable", "on" if heartbeat_ok else "off")
    if cert_days is not None:
        set_entity(
            "sensor.haprox_certificate_days", str(cert_days),
            {"expires_at": payload["cert_expires"]},
        )
    set_entity("sensor.haprox_external_url", f"https://{state['domain']}")
    set_entity(
        "sensor.haprox_status",
        compute_status(tunnel_ok, cert_days, bool(payload["last_error"])),
    )

    if cert_days is not None and cert_days < CERT_WARN_DAYS:
        log("heartbeat", f"Zertifikat läuft in {cert_days} Tagen ab.")
        notify_cert_expiry(state["domain"], cert_days)


SETUP_POLL_SECONDS = 2


def run_setup_progress(state: dict) -> None:
    """Setup-Fortschrittsanzeige, Stufen 2-5 -- Stufe 1 setzt enroll.py
    bereits, bevor dieser Prozess ueberhaupt
    existiert (cont-init.d laeuft vollstaendig vor services.d). Kurzer
    Takt (SETUP_POLL_SECONDS) nur waehrend des Setups, damit die Anzeige
    zeitnah reagiert -- der normale heartbeat_interval (Minuten) waere
    fuer 30-Sekunden-Zeitueberschreitungen viel zu grob. Kehrt zurueck,
    sobald Stufe 5 erreicht ist oder gar kein Setup im Gange ist
    (Bestandsinstallation ohne setup_progress.json)."""
    progress = haprox_common.load_setup_progress()
    if progress is None or progress.get("done"):
        return

    ha_core_port = _fetch_ha_core_port()

    while True:
        progress = haprox_common.load_setup_progress()
        if progress is None or progress.get("done"):
            return
        step = progress["step"]

        handshake_ever = tunnel_up_once()
        cert_ready = cert_files_exist(state["domain"])
        nginx_ready = cert_ready and nginx_ok(state["wg_ip"]) and _local_core_reachable(ha_core_port)

        target = step
        # Stufen 3+4 sind praktisch gleichzeitig: cert.py versucht schon
        # seit Container-Start unabhaengig, acme-dns zu erreichen (das nur
        # ueber den Tunnel geht) -- sobald der erste Handshake da ist, laeuft
        # der Zertifikatsbezug faktisch schon.
        if handshake_ever:
            target = max(target, 4)
        if nginx_ready:
            target = 5

        # Nie eine Stufe ueberspringen -- falls zwischen zwei Polls mehrere
        # Bedingungen zugleich erfuellt wurden, Zwischenstufen im selben
        # Durchlauf kurz durchlaufen statt direkt draufzuspringen.
        while step < target:
            step += 1
            haprox_common.enter_step("heartbeat", step)

        if step == 5:
            haprox_common.dismiss_notification("haprox_setup_stuck", "heartbeat")
            haprox_common.notify(
                "haprox_setup_complete", "haprox: Setup abgeschlossen",
                f"Deine Instanz ist eingerichtet und unter {state['domain']} erreichbar.",
                "heartbeat",
            )
            return

        progress = haprox_common.load_setup_progress()
        started = datetime.fromisoformat(progress["step_started_at"])
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        timeout = haprox_common.STEP_TIMEOUTS.get(step)
        if timeout and elapsed > timeout and not progress.get("stuck"):
            haprox_common.mark_stuck("heartbeat", step)

        time.sleep(SETUP_POLL_SECONDS)


def cert_files_exist(domain: str) -> bool:
    certs = LEGO_PATH / "certificates"
    return (certs / f"{domain}.crt").exists() and (certs / f"{domain}.key").exists()


def main() -> None:
    state = load_state()
    options = load_options()
    interval = int(options.get("heartbeat_interval") or DEFAULT_HEARTBEAT_INTERVAL)

    run_setup_progress(state)

    while True:
        payload = gather_payload(state)
        ok = send_heartbeat(state, payload)
        update_entities(state, payload, ok)
        time.sleep(interval)


if __name__ == "__main__":
    main()
