#!/usr/bin/env python3
"""Enrollment + Zustandshaltung fuer haprox-connect (ADDON-SPEC.md Abschnitt 3+8).

Laeuft einmalig beim Add-on-Start (etc/cont-init.d/10-enroll.sh). Stdlib
only -- kein pip/requests im Image, siehe build.yaml/Dockerfile.

Pfade sind ueber Umgebungsvariablen umbiegbar (HAPROX_OPTIONS_PATH,
HAPROX_STATE_PATH), damit sich das Skript ausserhalb eines echten
HA-Add-on-Containers testen laesst (siehe Plan, Abschnitt Verifikation).
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
    """ADDON-SPEC.md Abschnitt 2: der Token wird nach erfolgreichem Enrollment
    vom Add-on selbst aus der Konfiguration geloescht, damit er nicht
    dauerhaft im Klartext in den Add-on-Optionen steht. Fehler hier sind
    kein Abbruchgrund -- der Zustand ist bereits sicher persistiert."""
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
        # Standard-SSL-Kontext die volle Zertifikatskette (ADDON-SPEC.md
        # Abschnitt 3, "TLS").
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
    while True:
        try:
            response = post_enroll(enroll_url, token, public_key, ha_version, addon_version)
            break
        except InvalidToken:
            log(
                "enroll",
                "Der Code wurde nicht akzeptiert. Codes sind 30 Minuten gueltig "
                "und koennen nur einmal verwendet werden. Lass dir einen neuen "
                "Code geben.",
            )
            sys.exit(1)
        except RateLimited:
            log("enroll", "Zu viele Versuche in kurzer Zeit. Bitte spaeter erneut versuchen.")
            sys.exit(1)
        except urllib.error.URLError as exc:
            log("enroll", f"Relay nicht erreichbar ({exc}). Versuche es in {delay}s erneut.")
            time.sleep(delay)
            delay = min(delay * 2, BACKOFF_MAX_SECONDS)

    response["private_key"] = private_key
    return response


def write_state_atomic(state: dict) -> None:
    """Abschnitt 8, 'Abgebrochenes Enrollment': die Antwort wird als
    Erstes vollstaendig persistiert, erst danach wird irgendetwas
    konfiguriert. Temp-Datei + os.replace fuer Atomaritaet, Modus 600
    weil der private Schluessel drinsteht."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, indent=2))
    tmp_path.chmod(0o600)
    os.replace(tmp_path, STATE_PATH)


def main() -> None:
    if STATE_PATH.exists():
        log("enroll", "Bereits registriert, ueberspringe Enrollment.")
        return

    options = load_options()
    state = enroll(options)
    write_state_atomic(state)
    log("enroll", f"Standort registriert: {state['domain']}")
    clear_enrollment_token()


if __name__ == "__main__":
    main()
