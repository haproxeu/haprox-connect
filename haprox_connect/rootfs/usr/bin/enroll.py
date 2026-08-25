#!/usr/bin/env python3
"""Enrollment + Zustandshaltung fuer haprox-connect.

Laeuft einmalig beim Add-on-Start (etc/cont-init.d/10-enroll.sh). Stdlib
only -- kein pip/requests im Image, siehe build.yaml/Dockerfile.

Pfade sind ueber Umgebungsvariablen umbiegbar (HAPROX_OPTIONS_PATH,
HAPROX_STATE_PATH), damit sich das Skript ausserhalb eines echten
HA-Add-on-Containers testen laesst.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import haprox_common
from haprox_common import log, supervisor_request

OPTIONS_PATH = Path(os.environ.get("HAPROX_OPTIONS_PATH", "/data/options.json"))
STATE_PATH = haprox_common.STATE_PATH

BACKOFF_START_SECONDS = 5
BACKOFF_MAX_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 15


def load_options() -> dict:
    return json.loads(OPTIONS_PATH.read_text())


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


def clear_enrollment_token() -> None:
    """Der Token wird nach erfolgreichem Enrollment vom Add-on selbst aus
    der Konfiguration geloescht, damit er nicht dauerhaft im Klartext in
    den Add-on-Optionen steht. Fehler hier sind kein Abbruchgrund -- der
    Zustand ist bereits sicher persistiert."""
    try:
        supervisor_request("POST", "/addons/self/options", {"options": {"enrollment_token": ""}})
    except Exception as exc:
        log("enroll", f"Konnte den Enrollment-Code nicht aus der Konfiguration loeschen: {exc}")


def generate_keypair() -> tuple[str, str]:
    private_key = subprocess.run(
        ["wg", "genkey"], capture_output=True, check=True, text=True
    ).stdout.strip()
    public_key = subprocess.run(
        ["wg", "pubkey"], input=private_key, capture_output=True, check=True, text=True
    ).stdout.strip()
    return private_key, public_key


class InvalidToken(RuntimeError):
    pass


class RateLimited(RuntimeError):
    pass


def post_enroll(enroll_url: str, token: str, public_key: str, ha_version: str, addon_version: str) -> dict:
    """Ein Versuch. Wirft InvalidToken/RateLimited (kein Retry sinnvoll)
    oder urllib.error.URLError (Verbindungsfehler, Aufrufer retried)."""
    body = json.dumps(
        {
            "token": token,
            "public_key": public_key,
            "ha_version": ha_version,
            "addon_version": addon_version,
        }
    ).encode()
    req = urllib.request.Request(
        f"{enroll_url}/enroll", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        # Kein verify=False-Aequivalent: urllib prueft mit dem
        # Standard-SSL-Kontext die volle Zertifikatskette.
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise InvalidToken() from exc
        if exc.code == 429:
            raise RateLimited() from exc
        raise  # 5xx u.ae. -- vom Aufrufer als Verbindungsfehler behandelt (URLError-Basisklasse)


def enroll(options: dict) -> dict:
    token = options.get("enrollment_token", "").strip()
    if not token:
        log("enroll", "Kein Code eingetragen. Trage einen Enrollment-Code ein und starte das Add-on neu.")
        sys.exit(1)

    enroll_url = options.get("enroll_url") or "https://enroll.haprox.eu"

    private_key, public_key = generate_keypair()
    ha_version = fetch_ha_version()
    addon_version = fetch_addon_version()

    delay = BACKOFF_START_SECONDS
    start = time.monotonic()
    while True:
        try:
            response = post_enroll(enroll_url, token, public_key, ha_version, addon_version)
            break
        except InvalidToken:
            # Einzige echte Ausnahme vom "niemals aufgeben"-Prinzip sonst
            # ueberall in diesem Skript -- ein abgelehnter Code repariert
            # sich nicht von selbst durch Warten, im Gegensatz zu einem
            # unerreichbaren Relay.
            log(
                "enroll",
                "Der Code wurde nicht akzeptiert. Codes sind 30 Minuten gueltig "
                "und koennen nur einmal verwendet werden. Lass dir einen neuen "
                "Code geben.",
            )
            haprox_common.mark_stuck(
                "enroll", 1, "Code ungueltig oder abgelaufen -- neuen Code anfordern."
            )
            sys.exit(1)
        except RateLimited:
            log("enroll", "Zu viele Versuche in kurzer Zeit. Bitte spaeter erneut versuchen.")
            haprox_common.mark_stuck(
                "enroll", 1, "Zu viele Versuche -- bitte spaeter erneut versuchen."
            )
            sys.exit(1)
        except urllib.error.URLError as exc:
            log("enroll", f"Relay nicht erreichbar ({exc}). Versuche es in {delay}s erneut.")
            if time.monotonic() - start > haprox_common.STEP_TIMEOUTS[1]:
                haprox_common.mark_stuck("enroll", 1)
            time.sleep(delay)
            delay = min(delay * 2, BACKOFF_MAX_SECONDS)

    response["private_key"] = private_key
    return response


def write_state_atomic(state: dict) -> None:
    """Fuer den Fall eines abgebrochenen Enrollments: die Antwort wird
    als Erstes vollstaendig persistiert, erst danach wird irgendetwas
    konfiguriert. Temp-Datei + os.replace fuer Atomaritaet, Modus 600
    weil der private Schluessel drinsteht."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, indent=2))
    tmp_path.chmod(0o600)
    os.replace(tmp_path, STATE_PATH)


def main() -> None:
    options = load_options()
    token = options.get("enrollment_token", "").strip()

    if STATE_PATH.exists():
        if not token:
            log("enroll", "Bereits registriert, ueberspringe Enrollment.")
            return
        # Echter Bug, mit-behoben: main() ueberprang Enrollment bisher IMMER,
        # sobald der State existierte -- auch wenn ein neuer, gueltiger Token
        # eingetragen war. Der "Zuruecksetzen"-Weg aus der Management-UI
        # (neuer Token fuer denselben Standort) funktionierte dadurch nie,
        # nur Deinstallieren/Neuinstallieren loeschte /data ungewollt mit.
        log(
            "enroll",
            "Neuer Code trotz bestehender Registrierung -- Standort wird zurueckgesetzt.",
        )
        STATE_PATH.unlink()
        haprox_common.clear_setup_progress()
        haprox_common.dismiss_notification("haprox_setup_stuck", "enroll")
        haprox_common.dismiss_notification("haprox_setup_complete", "enroll")

    haprox_common.enter_step("enroll", 1)
    state = enroll(options)
    write_state_atomic(state)
    haprox_common.enter_step("enroll", 2)  # Staffelstab an heartbeat.py uebergeben
    log("enroll", f"Standort registriert: {state['domain']}")
    clear_enrollment_token()


if __name__ == "__main__":
    main()
