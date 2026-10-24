"""Drive app.py headlessly with streamlit.testing. The model is always a fake; no socket leaves this machine."""
import json
import socket

import pytest
from pytest_socket import SocketConnectBlockedError
from streamlit.testing.v1 import AppTest

import ramadi as r
from conftest import ROOT

APP = str(ROOT / "app.py")
TIMEOUT = 60


class Fake:
    def __init__(self, reply):
        self.reply, self.calls = reply, 0

    def __call__(self, model, prompt):
        self.calls += 1
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply(prompt) if callable(self.reply) else self.reply


@pytest.fixture
def downloads(monkeypatch):
    """Record every Markdown document the app hands to the download button."""
    seen, real = [], r.to_markdown
    monkeypatch.setattr(r, "to_markdown", lambda *args: seen.append(real(*args)) or seen[-1])
    return seen


def start(monkeypatch, models=("fake:1b",), reply=None):
    monkeypatch.setattr(r, "list_models", lambda: list(models))
    fake = Fake(reply)
    monkeypatch.setattr(r, "ollama_chat", fake)
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    assert not at.exception
    return at, fake


def widget(elements, label):
    return next(e for e in elements if e.label.startswith(label))


def metric(at, label):
    return widget(at.metric, label)


def set_sidebar(at, **values):
    labels = {"roof": "Roof area", "people": "People", "showers": "Showers", "laundry": "Laundry",
              "capacity": "Harvest tank"}
    for key, v in values.items():
        if key in labels:
            widget(at.sidebar.slider, labels[key]).set_value(v)
        elif key == "gov":
            widget(at.sidebar.selectbox, "Governorate").set_value(v)
        else:
            widget(at.sidebar.radio, {"budget": "Budget", "year": "Year type", "lang": "Blueprint language"}[key]
                   ).set_value(v)
    at.run()
    assert not at.exception
    return at


def generate(at):
    widget(at.sidebar.button, "Generate blueprint").click()
    at.run()
    assert not at.exception
    return at


def model_plan(lang="en", budget="low", **overrides):
    p = r.template_blueprint({"roof_m2": 80, "people": 3}, budget, lang).model_dump()
    p["summary"] = "Fake model plan." if lang == "en" else "خطة من النموذج."
    p.update(overrides)
    return json.dumps(p, ensure_ascii=False)


def html_text(at):
    return "\n".join(m.value for m in at.markdown)


def engine(gov="Amman (west)", roof=120, people=5, showers=5, laundry=4, capacity=2.0, year="average",
           budget="low", lang="en"):
    t = r.load_tables()
    a = r.assumption_values(t.assumptions)
    profile = r.make_profile(t.rain, gov, roof, people, showers, laundry, capacity, year)
    res = r.simulate(profile, t.shares, a)
    cost = r.plan_cost(r.price(r.template_blueprint(profile, budget, lang), t.catalog))
    return res, r.impact(res["water"], cost, a), a


# ---------------------------------------------------------------- 1. happy path

def test_happy_path(monkeypatch, downloads):
    at, fake = start(monkeypatch, reply=model_plan())
    inputs = dict(gov="Irbid", roof=200, people=4, showers=6, laundry=3, capacity=3.0, year="wet", budget="low")
    set_sidebar(at, **inputs)

    res, imp, _ = engine(**inputs)
    assert metric(at, "Water reused").value == f"{res['water']:.1f} m³/yr"
    assert metric(at, "Tanker trips avoided").value == f"{imp['trips']:.1f} /yr"
    assert metric(at, "Saved").value == f"{imp['jod']:.0f} JOD/yr"
    assert metric(at, "CO₂ cut").value == f"{imp['co2']:.0f} kg/yr"
    assert metric(at, "Payback").value == r.format_payback(imp["payback_months"])

    generate(at)
    assert fake.calls == 1
    assert not at.warning
    assert any("Generated on this laptop by fake:1b" in c.value for c in at.caption)
    page = html_text(at)
    assert "Fake model plan." in page and "<ol><li>" in page
    assert "Safety checks passed: 6 of 6" in page
    bom = at.dataframe[0].value
    assert {"item", "qty", "unit_jod", "total_jod"} <= set(bom.columns) and (bom["total_jod"] > 0).all()
    assert {"First-flush diverter kit", "Non-potable warning labels"} <= set(bom["item"])
    assert at.get("download_button")[0].label == "Download plan (.md)"
    md = downloads[-1]
    assert all(w in md for w in r.WARNINGS["en"]) and r.DISCLAIMER["en"] in md


def test_model_html_is_escaped(monkeypatch):
    at, _ = start(monkeypatch, reply=model_plan(summary="<img src=x onerror=alert(1)> plan"))
    generate(at)
    page = html_text(at)
    assert "<img" not in page and "&lt;img src=x onerror=alert(1)&gt; plan" in page


# ---------------------------------------------------------------- 2. fallback paths

TEMPLATE_SUMMARY = "Baseline plan for a"


@pytest.mark.parametrize("reply,calls,why", [
    ("Sure! Here is a plan: buy a big tank.", r.MAX_ATTEMPTS, r.NOT_JSON),
    (model_plan(materials=[{"item_id": "gold_tap", "quantity": 1, "reason": "x"}]), r.MAX_ATTEMPTS, r.UNKNOWN_ITEM),
    (ConnectionRefusedError(111, "Connection refused"), 1, "unavailable"),
    (TimeoutError("timed out"), 1, "timeout"),
    (r.ModelNotFound("fake:1b is not pulled"), 1, "model_not_pulled"),
])
def test_fallback_paths(monkeypatch, downloads, reply, calls, why):
    at, fake = start(monkeypatch, reply=reply)
    generate(at)
    assert fake.calls == calls
    notice = at.warning[0].value
    assert notice.startswith("Showing the built-in template plan") and why in notice
    assert TEMPLATE_SUMMARY in html_text(at)
    assert r.DISCLAIMER["en"] in downloads[-1]


def test_fallback_over_budget_total(monkeypatch):
    monkeypatch.setattr(r, "budget_cap", lambda a, budget: 50.0)
    at, fake = start(monkeypatch, reply=model_plan())
    generate(at)
    assert fake.calls == r.MAX_ATTEMPTS
    assert r.BOM_OVER_BUDGET in at.warning[0].value and TEMPLATE_SUMMARY in html_text(at)


def test_ollama_not_installed(monkeypatch):
    # Real list_models against a closed local port, as on a laptop without Ollama.
    fake = Fake(model_plan())
    monkeypatch.setattr(r, "ollama_chat", fake)
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    assert not at.exception
    assert any("Ollama is not running" in c.value for c in at.sidebar.caption)
    generate(at)
    assert fake.calls == 0
    assert "No local model was available" in at.warning[0].value and TEMPLATE_SUMMARY in html_text(at)


# ---------------------------------------------------------------- 3. Arabic

def test_arabic_plan_and_download(monkeypatch, downloads):
    at, _ = start(monkeypatch, reply=model_plan("ar"))
    set_sidebar(at, lang="ar")
    generate(at)
    assert "rc-rtl" in html_text(at) and "خطة من النموذج." in html_text(at)
    md = downloads[-1]
    assert md.startswith('<div dir="rtl" lang="ar">')
    assert all(w in md for w in r.WARNINGS["ar"]) and r.DISCLAIMER["ar"] in md
    assert r.DISCLAIMER["en"] not in md


def test_arabic_template_fallback(monkeypatch, downloads):
    at, _ = start(monkeypatch, reply="prose")
    set_sidebar(at, lang="ar")
    generate(at)
    assert at.warning and all(w in downloads[-1] for w in r.WARNINGS["ar"])


# ---------------------------------------------------------------- 4. Sareef toggle

def test_sareef_toggle_signs(monkeypatch):
    at, _ = start(monkeypatch)
    res, imp, a = engine()
    labels = ("Tanker trips a year", "JOD a year on this water", "kg CO₂ a year")
    on = {k: metric(at, k) for k in labels}
    for m in on.values():
        assert m.delta and m.delta.startswith("-")
    assert float(on[labels[0]].delta) == pytest.approx(-imp["trips"], abs=0.05)

    at.toggle[0].set_value(False).run()
    off = {k: metric(at, k) for k in labels}
    assert all(not m.delta for m in off.values())
    for k in labels:
        assert float(off[k].value) > float(on[k].value)
    sc = r.sareef(res, a, False)
    assert off[labels[0]].value == f"{sc['now']['trips']:.1f}"


def test_community_slider(monkeypatch):
    at, _ = start(monkeypatch)
    res, imp, _ = engine()
    widget(at.slider, "Scale to homes").set_value(1000).run()
    text = " ".join(m.value for m in at.markdown)
    assert f"1000 homes: **{res['water'] * 1000:,.0f} m³**" in text


# ---------------------------------------------------------------- 5. zero inputs

def test_zero_inputs(monkeypatch):
    at, _ = start(monkeypatch)
    set_sidebar(at, roof=0, people=0, laundry=0)
    assert metric(at, "Water reused").value == "0.0 m³/yr"
    assert metric(at, "Payback").value == "n/a"
    generate(at)
    assert "Safety checks passed: 6 of 6" in html_text(at)


# ---------------------------------------------------------------- 6. offline

@pytest.mark.filterwarnings("ignore::UserWarning")
def test_external_sockets_blocked():
    with pytest.raises(SocketConnectBlockedError):
        socket.create_connection(("192.0.2.1", 80), timeout=1)  # TEST-NET-1


# ---------------------------------------------------------------- 7. assumptions tab

def test_assumptions_tab_lists_every_constant(monkeypatch):
    at, _ = start(monkeypatch)
    t = r.load_tables()
    frames = [d.value for d in at.dataframe]
    shown = next(f for f in frames if "parameter" in f.columns)
    assert set(shown["parameter"]) == set(t.assumptions["parameter"])
    assert {"source", "status", "value", "unit"} <= set(shown.columns)
    shares = r.read_table("monthly_share.csv")
    for table, key in ((t.rain, "governorate"), (shares, "month"), (t.catalog, "item_id"), (t.plants, "plant_id")):
        f = next(f for f in frames if key in f.columns)
        assert set(f[key]) == set(table[key]) and {"source", "status"} <= set(f.columns)
