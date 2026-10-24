"""Privacy, offline and edge cases: only localhost is contacted, no file is written, no user text is logged,
Arabic downloads survive UTF-8."""
import json
import logging
import socket
from pathlib import Path

import api
import ramadi as r

ROOT = Path(__file__).parent.parent
BODY = {"governorate": "Irbid", "roof_m2": 120, "people": 5, "showers_pp": 5, "laundry_loads": 4,
        "capacity_m3": 2.0, "budget": "low", "lang": "en"}
SECRET = "my-neighbour-Abu-Khaled-0791234567"
GARDEN = json.dumps({"language": "en", "summary": "One olive.", "plants": [{"plant_id": "olive", "count": 1, "reason": "Shade."}],
                     "care_steps": ["Plant in November.", "Mulch well.", "Check drippers."]})


def full_run():
    """Every backend route, with fake models: options (lists Ollama models), plan, generate, garden."""
    api.options()
    api.plan(api.PlanRequest(**BODY))
    api.generate(api.GenerateRequest(**BODY, model="fake"), chat=lambda m, p: "prose")
    api.garden(api.GardenRequest(**BODY, wishes=SECRET, model="fake"), chat=lambda m, p, s: GARDEN)
    api.garden(api.GardenRequest(**BODY, wishes=SECRET, model="fake"), chat=lambda m, p, s: "prose")


def test_only_localhost_is_ever_contacted(monkeypatch):
    hosts = []
    real = socket.socket.connect

    def record(self, address):
        hosts.append(address[0] if isinstance(address, tuple) else address)
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", record)
    full_run()
    assert hosts and set(hosts) <= {"127.0.0.1", "localhost", "::1"}  # the Ollama model list, on a closed local port


def snapshot():
    skip = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".hypothesis", "dist"}
    return {p: p.stat().st_mtime for p in ROOT.rglob("*") if p.is_file() and not skip & set(p.parts)}


def test_a_full_run_writes_no_files():
    before = snapshot()
    full_run()
    assert snapshot() == before


def test_user_text_never_reaches_the_logs(caplog):
    with caplog.at_level(logging.DEBUG):
        full_run()
    assert SECRET not in caplog.text and "Abu" not in caplog.text


def test_arabic_download_round_trips_as_utf8():
    md = api.plan(api.PlanRequest(**{**BODY, "lang": "ar"}))["markdown"]
    data = md.encode("utf-8")
    assert data.decode("utf-8") == md and '<div dir="rtl" lang="ar">' in md
    assert all(w in md for w in r.WARNINGS["ar"]) and r.DISCLAIMER["ar"] in md


def test_download_contains_plan_parts_and_warnings():
    out = api.plan(api.PlanRequest(**BODY))
    md = out["markdown"]
    assert "## Rainwater" in md and "## Materials" in md and "## Safety rules" in md
    assert all(row["item"] in md for row in out["plan"]["bom"])
