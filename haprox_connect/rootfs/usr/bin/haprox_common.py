"""Gemeinsame Helfer fuer haprox-connect (enroll.py, cert.py, heartbeat.py).

Stdlib only -- kein pip/requests im Image, siehe build.yaml/Dockerfile.
Pfade ueber Umgebungsvariablen umbiegbar, damit sich die Skripte
ausserhalb eines echten HA-Add-on-Containers testen lassen.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

STATE_PATH = Path(os.environ.get("HAPROX_STATE_PATH", "/data/haprox.json"))
SUPERVISOR_API = os.environ.get("HAPROX_SUPERVISOR_API", "http://supervisor")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
REQUEST_TIMEOUT_SECONDS = 15


def log(component: str, message: str) -> None:
    print(f"[haprox-connect/{component}] {message}", flush=True)


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text())


def supervisor_request(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{SUPERVISOR_API}{path}", method=method)
    req.add_header("Authorization", f"Bearer {SUPERVISOR_TOKEN}")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=data, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        return json.load(resp)
