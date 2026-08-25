"""Gemeinsame Helfer fuer haprox-connect (enroll.py, cert.py, heartbeat.py).

Stdlib only -- kein pip/requests im Image, siehe build.yaml/Dockerfile.
Pfade ueber Umgebungsvariablen umbiegbar, damit sich die Skripte
ausserhalb eines echten HA-Add-on-Containers testen lassen.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(os.environ.get("HAPROX_STATE_PATH", "/data/haprox.json"))
SETUP_PROGRESS_PATH = Path(
    os.environ.get("HAPROX_SETUP_PROGRESS_PATH", "/data/setup_progress.json")
)
SUPERVISOR_API = os.environ.get("HAPROX_SUPERVISOR_API", "http://supervisor")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
REQUEST_TIMEOUT_SECONDS = 15

# Setup-Fortschrittsanzeige: 5 Stufen, jede mit eigener
# Zeitueberschreitung (Sekunden) und Hinweistext. Stufe 5 hat keine
# Zeitueberschreitung -- "Bereit" ist der Endzustand.
STEP_LABELS = {
    1: "Code wird geprueft",
    2: "Verbindung wird aufgebaut",
    3: "Verbindung steht",
    4: "Zertifikat wird bezogen",
    5: "Bereit",
}
STEP_TIMEOUTS = {1: 30, 2: 60, 3: 30, 4: 120}
STEP_TIMEOUT_HINTS = {
    1: "Code wird abgelehnt oder Relay antwortet nicht",
    2: "Tunnel kommt nicht zustande",
    3: "acme-dns antwortet nicht -- Tunnel pruefen",
    4: "Zertifikat wird nicht ausgestellt",
}


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


def set_entity(component: str, entity_id: str, state_value: str, attributes: dict | None = None) -> None:
    try:
        supervisor_request(
            "POST", f"/core/api/states/{entity_id}",
            {"state": state_value, "attributes": attributes or {}},
        )
    except Exception as exc:
        log(component, f"Entitaet {entity_id} konnte nicht gesetzt werden: {exc}")


def notify(notification_id: str, title: str, message: str, component: str = "common") -> None:
    try:
        supervisor_request(
            "POST", "/core/api/services/persistent_notification/create",
            {"title": title, "message": message, "notification_id": notification_id},
        )
    except Exception as exc:
        log(component, f"Persistente Benachrichtigung '{notification_id}' fehlgeschlagen: {exc}")


def dismiss_notification(notification_id: str, component: str = "common") -> None:
    try:
        supervisor_request(
            "POST", "/core/api/services/persistent_notification/dismiss",
            {"notification_id": notification_id},
        )
    except Exception as exc:
        log(component, f"Benachrichtigung '{notification_id}' konnte nicht entfernt werden: {exc}")


def load_setup_progress() -> dict | None:
    if not SETUP_PROGRESS_PATH.exists():
        return None
    return json.loads(SETUP_PROGRESS_PATH.read_text())


def save_setup_progress(data: dict) -> None:
    SETUP_PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETUP_PROGRESS_PATH.write_text(json.dumps(data))


def clear_setup_progress() -> None:
    SETUP_PROGRESS_PATH.unlink(missing_ok=True)


def enter_step(component: str, step: int) -> None:
    """Neue Setup-Stufe erreicht -- Fortschrittsdatei schreiben und
    sensor.haprox_status auf setting_up_{step}_5 mit den passenden
    Attributen setzen. Ueberschreibt einen etwaigen 'stuck'-Zustand der
    vorherigen Stufe (die ist ja jetzt ueberwunden)."""
    now = datetime.now(timezone.utc)
    timeout = STEP_TIMEOUTS.get(step)
    step_timeout_at = None
    if timeout is not None:
        step_timeout_at = datetime.fromtimestamp(now.timestamp() + timeout, tz=timezone.utc).isoformat()
    data = {
        "step": step,
        "step_started_at": now.isoformat(),
        "stuck": False,
        "hint": None,
        "done": step == 5,
    }
    save_setup_progress(data)
    set_entity(
        component, "sensor.haprox_status", f"setting_up_{step}_5",
        {
            "step": step,
            "step_total": 5,
            "step_label": STEP_LABELS[step],
            "step_started_at": data["step_started_at"],
            "step_timeout_at": step_timeout_at,
            "stuck": False,
            "hint": None,
        },
    )


def mark_stuck(component: str, step: int, hint: str | None = None) -> None:
    """Nur beim Uebergang stuck=False -> True aufrufen (Aufrufer prueft
    das). Kein wiederholtes Benachrichtigen pro Poll."""
    progress = load_setup_progress() or {}
    if progress.get("stuck") and progress.get("step") == step:
        return
    hint = hint or STEP_TIMEOUT_HINTS.get(step, "")
    progress.update({"step": step, "stuck": True, "hint": hint})
    save_setup_progress(progress)
    set_entity(
        component, "sensor.haprox_status", f"setting_up_{step}_5",
        {
            "step": step,
            "step_total": 5,
            "step_label": STEP_LABELS[step],
            "step_started_at": progress.get("step_started_at"),
            "step_timeout_at": None,
            "stuck": True,
            "hint": hint,
        },
    )
    notify("haprox_setup_stuck", f"haprox: Setup haengt bei Schritt {step}/5", hint, component)
