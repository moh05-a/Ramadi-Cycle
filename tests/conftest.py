import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import ramadi as r  # noqa: E402

PROFILE = {"governorate": "Irbid", "rain_mm": 470, "roof_m2": 120, "people": 5, "showers_pp": 5,
           "laundry_loads": 4, "capacity_m3": 2.0, "year": "average"}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def no_real_ollama(monkeypatch):
    """Point the Ollama URL at a closed local port so no test can reach a model running on this machine."""
    monkeypatch.setattr(r, "OLLAMA_URL", f"http://127.0.0.1:{free_port()}")
    # No OpenRouter key in tests, so cloud models never appear and no test can spend credit.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODELS", raising=False)


@pytest.fixture(scope="session")
def tables():
    return r.load_tables()


@pytest.fixture(scope="session")
def a(tables):
    return r.assumption_values(tables.assumptions)
