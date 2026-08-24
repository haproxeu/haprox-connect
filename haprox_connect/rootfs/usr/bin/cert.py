#!/usr/bin/env python3
"""Zertifikatsbezug + Erneuerung fuer haprox-connect (addon.md Abschnitt 5).

Laeuft als s6-Longrun-Dienst (etc/services.d/cert/run), nachdem der
Tunnel steht (Schritt 2). Nutzt `lego --dns acme-dns` mit den beim
Enrollment erhaltenen Zugangsdaten -- gleiches Speicherformat wie
`haprox/manage.py:acme_dns_storage_json()` am Relay
(ACME_DNS_STORAGE_PATH), nur hier selbst geschrieben statt manuell im
offiziellen Let's-Encrypt-Add-on eingetragen.

Stdlib only, siehe enroll.py fuer dieselbe Konvention (Pfade ueber
Umgebungsvariablen umbiegbar zum Testen ausserhalb eines echten
Add-on-Containers).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

STATE_PATH = Path(os.environ.get("HAPROX_STATE_PATH", "/data/haprox.json"))
LEGO_PATH = Path(os.environ.get("HAPROX_LEGO_PATH", "/data/lego"))
LEGO_BIN = os.environ.get("HAPROX_LEGO_BIN", "/usr/local/bin/lego")

BACKOFF_START_SECONDS = 5
BACKOFF_MAX_SECONDS = 300
RENEW_CHECK_INTERVAL_SECONDS = 12 * 60 * 60  # addon.md Abschnitt 5: kein festes
# Erneuerungsintervall hartkodieren -- das entscheidet lego selbst per
# ARI beim `renew`-Aufruf. Dies ist nur die Pruef-Frequenz.


def log(message: str) -> None:
    print(f"[haprox-connect/cert] {message}", flush=True)


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text())


def storage_path() -> Path:
    return LEGO_PATH / "acme-dns-storage.json"


def write_acme_dns_storage(state: dict) -> None:
    """Gleiches Format wie haprox/manage.py:acme_dns_storage_json() am
    Relay -- ein JSON-Objekt keyed auf die Domain."""
    acmedns = state["acmedns"]
    data = {
        state["domain"]: {
            "username": acmedns["username"],
            "password": acmedns["password"],
            "fulldomain": acmedns["fulldomain"],
            "subdomain": acmedns["subdomain"],
            "allowfrom": [],
        }
    }
    storage_path().parent.mkdir(parents=True, exist_ok=True)
    storage_path().write_text(json.dumps(data, indent=2))


def lego_env(state: dict) -> dict:
    env = os.environ.copy()
    env["ACME_DNS_API_BASE"] = state["acmedns_api"]
    env["ACME_DNS_STORAGE_PATH"] = str(storage_path())
    return env


def cert_files_exist(domain: str) -> bool:
    certs = LEGO_PATH / "certificates"
    return (certs / f"{domain}.crt").exists() and (certs / f"{domain}.key").exists()


def lego_run(state: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            LEGO_BIN, "--accept-tos", "--path", str(LEGO_PATH),
            "--dns", "acme-dns", "--domains", state["domain"], "run",
        ],
        env=lego_env(state), capture_output=True, text=True,
    )


def lego_renew(state: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            LEGO_BIN, "--accept-tos", "--path", str(LEGO_PATH),
            "--dns", "acme-dns", "--domains", state["domain"], "renew",
        ],
        env=lego_env(state), capture_output=True, text=True,
    )


def reload_nginx() -> None:
    try:
        subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True, timeout=10)
    except Exception as exc:
        log(f"nginx-Reload nach Erneuerung fehlgeschlagen (evtl. laeuft nginx noch nicht): {exc}")


def acquire_initial_certificate(state: dict) -> None:
    """Erster Bezug -- Backoff bei Fehlschlag (Tunnel/acme-dns evtl. noch
    nicht erreichbar), niemals aufgeben (addon.md Abschnitt 8, sinngemaess
    auf den Zertifikatsbezug uebertragen: kein Aufgeben, klare
    Log-Zeile statt Stacktrace)."""
    if cert_files_exist(state["domain"]):
        log(f"Zertifikat fuer {state['domain']} existiert bereits.")
        return

    write_acme_dns_storage(state)
    delay = BACKOFF_START_SECONDS
    while True:
        result = lego_run(state)
        if result.returncode == 0:
            log(f"Zertifikat fuer {state['domain']} erfolgreich bezogen.")
            return
        log(
            f"Zertifikatsbezug fehlgeschlagen (lego-Exitcode {result.returncode}): "
            f"{result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'kein Fehlertext'}. "
            f"Versuche es in {delay}s erneut."
        )
        time.sleep(delay)
        delay = min(delay * 2, BACKOFF_MAX_SECONDS)


def renewal_loop(state: dict) -> None:
    while True:
        time.sleep(RENEW_CHECK_INTERVAL_SECONDS)
        result = lego_renew(state)
        if result.returncode != 0:
            log(f"Erneuerungs-Check fehlgeschlagen: {result.stderr.strip()}")
            continue
        if "no renewal" in result.stdout.lower() or "not needed" in result.stdout.lower():
            continue
        log(f"Zertifikat fuer {state['domain']} erneuert.")
        reload_nginx()


def main() -> None:
    state = load_state()
    acquire_initial_certificate(state)
    renewal_loop(state)


if __name__ == "__main__":
    main()
