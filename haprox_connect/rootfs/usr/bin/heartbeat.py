#!/usr/bin/env python3
"""Heartbeat + Statusentitaeten fuer haprox-connect (addon.md Abschnitt 6+7).

Laeuft als s6-Longrun-Dienst (etc/services.d/heartbeat/run), meldet sich
alle heartbeat_interval Sekunden beim Relay und setzt danach die
Statusentitaeten ueber die Supervisor-API -- unabhaengig davon, ob der
Heartbeat selbst ankam (die Entitaeten spiegeln den lokal bekannten
Zustand, addon.md Abschnitt 7: "Gesetzt vom Add-on").

sensor.haprox_traffic_month wird bewusst NICHT gesetzt -- die
Datenquelle (Relay-seitige Traffic-Historie) ist auf spaeter verschoben
(siehe Plan/STATUS.md). sensor.haprox_status kennt "enrolling"/
"pending_activation" nicht (siehe Plan, "Bekannte, dokumentierte
Luecken").
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
    """wg0-Handshake juenger als 5 Minuten (grosszuegig gegenueber
    PersistentKeepalive=25, toleriert kurze Aussetzer ohne sofort
    'tunnel_down' zu melden)."""
    result = subprocess.run(
        ["wg", "show", "wg0", "latest-handshakes"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return False
    parts = result.stdout.strip().split("\t")
    if len(parts) < 2:
        return False
    latest = int(parts[1])
    return latest > 0 and (time.time() - latest) < 300


def nginx_ok(wg_ip: str) -> bool:
    try:
        with socket.create_connection((wg_ip, 443), timeout=3):
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
        return supervisor_request("GET", "/core/info")["data"]["version"]
    except Exception:
        return ""


def fetch_addon_version() -> str:
    try:
        return supervisor_request("GET", "/addons/self/info")["data"]["version"]
    except Exception:
        return ""


def fetch_ha_os_version() -> str:
    try:
        return supervisor_request("GET", "/os/info")["data"]["version"]
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
    try:
        supervisor_request(
            "POST", f"/core/api/states/{entity_id}",
            {"state": state_value, "attributes": attributes or {}},
        )
    except Exception as exc:
        log("heartbeat", f"Entitaet {entity_id} konnte nicht gesetzt werden: {exc}")


def compute_status(tunnel_ok: bool, cert_days: int | None, has_error: bool) -> str:
    if not tunnel_ok:
        return "tunnel_down"
    if cert_days is None or has_error:
        return "cert_error"
    return "ok"


def notify_cert_expiry(domain: str, cert_days: int) -> None:
    """addon.md Abschnitt 8: ab 7 Tagen Restlaufzeit zusaetzlich zur
    Log-Warnung eine persistente Benachrichtigung in Home Assistant."""
    if cert_days >= CERT_CRITICAL_DAYS:
        return
    try:
        supervisor_request(
            "POST", "/core/api/services/persistent_notification/create",
            {
                "title": "haprox-connect: Zertifikat läuft bald ab",
                "message": (
                    f"Das Zertifikat für {domain} läuft in {cert_days} Tagen ab "
                    "und wurde noch nicht erneuert. Bitte die Add-on-Logs prüfen."
                ),
                "notification_id": "haprox_connect_cert_expiry",
            },
        )
    except Exception as exc:
        log("heartbeat", f"Persistente Benachrichtigung fehlgeschlagen: {exc}")


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


def main() -> None:
    state = load_state()
    options = load_options()
    interval = int(options.get("heartbeat_interval") or DEFAULT_HEARTBEAT_INTERVAL)

    while True:
        payload = gather_payload(state)
        ok = send_heartbeat(state, payload)
        update_entities(state, payload, ok)
        time.sleep(interval)


if __name__ == "__main__":
    main()
