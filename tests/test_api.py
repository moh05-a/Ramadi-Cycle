import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))
import api
import ramadi as r

BODY = {"governorate": "Irbid", "roof_m2": 120, "people": 5, "showers_pp": 5, "laundry_loads": 4,
        "capacity_m3": 2.0, "budget": "low", "lang": "en"}


def test_options_list_every_governorate():
    opts = api.options()
    assert [g["name"] for g in opts["governorates"]] == list(api.RAIN["governorate"])
    assert opts["limits"]["people"] == (0, 12)  # same as the Streamlit slider and the engine


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_plan_uses_engine_and_fixed_warnings(lang):
    out = api.plan(api.PlanRequest(**{**BODY, "lang": lang}))
    profile = out["profile"]
    res = r.simulate(profile, api.SHARES, api.A)
    assert out["result"]["water"] == pytest.approx(res["water"])
    assert out["warnings"] == r.WARNINGS[lang]
    assert out["disclaimer"] == r.DISCLAIMER[lang]
    assert out["plan"]["language"] == lang
    assert out["plan"]["cost"] == pytest.approx(sum(row["total_jod"] for row in out["plan"]["bom"]))
    assert out["impact"] == pytest.approx(r.impact(res["water"], out["plan"]["cost"], api.A))


def test_budget_costs_match_selected_plan():
    for budget in api.BUDGETS:
        out = api.plan(api.PlanRequest(**{**BODY, "budget": budget}))
        assert out["budget_costs"][budget] == out["plan"]["cost"]
    assert out["budget_costs"]["full"] != out["budget_costs"]["low"]


@pytest.mark.parametrize("bad", [{"people": -1}, {"people": 13}, {"roof_m2": 401}, {"capacity_m3": 0}, {"governorate": "Paris"},
                                 {"budget": "gold"}, {"lang": "fr"}, {"homes": 0},
                                 {"homes": 1001}, {"year": "monsoon"}])
def test_rejects_out_of_range_input(bad):
    with pytest.raises(ValidationError):
        api.PlanRequest(**{**BODY, **bad})


def test_http_roundtrip():
    server = api.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        post = lambda body: urllib.request.urlopen(urllib.request.Request(
            f"{base}/api/plan", json.dumps(body).encode(), {"Content-Type": "application/json"}))
        with post({**BODY, "lang": "ar"}) as resp:
            out = json.load(resp)
        assert out["warnings"] == r.WARNINGS["ar"]
        with pytest.raises(urllib.error.HTTPError) as e:
            post({**BODY, "people": 99})
        assert e.value.code == 422
    finally:
        server.shutdown()


def test_options_carry_method_models_and_every_table():
    opts = api.options()
    assert opts["models"] == []  # conftest points Ollama at a closed port
    assert opts["years"] == list(r.YEARS)
    assert opts["method"]["warnings"] == r.WARNINGS
    assert opts["method"]["banned_terms"] == r.BANNED_TERMS
    assert opts["method"]["schema"] == r.Blueprint.model_json_schema()
    tables = opts["tables"]
    assert [row["parameter"] for row in tables["assumptions"]] == list(api.ASSUMPTIONS["parameter"])
    assert len(tables["monthly_share"]) == 12
    assert {"rainfall", "catalog", "plants"} <= set(tables)
    json.dumps(opts)  # everything is JSON-serialisable


def test_plan_carries_balance_sareef_community_checks_and_prompt():
    out = api.plan(api.PlanRequest(**{**BODY, "year": "wet", "homes": 100}))
    res = r.simulate(out["profile"], api.SHARES, api.A)
    assert out["profile"]["year"] == "wet"
    assert [m["month"] for m in out["balance"]] == r.MONTHS
    assert out["sareef"]["delta"] == pytest.approx(r.sareef(res, api.A, True)["delta"])
    assert out["community"] == pytest.approx(r.community(res, out["impact"], 100))
    assert all(c["passed"] for c in out["plan"]["checks"]) and len(out["plan"]["checks"]) == 6
    assert out["plan"]["source"] == "template" and out["plan"]["notice"] is None
    assert out["payback"] == r.format_payback(out["impact"]["payback_months"])
    assert out["prompt"] == r.build_prompt(out["profile"], res, api.CATALOG, api.PLANTS, "low", "en")


def test_people_zero_allowed_like_the_engine():
    out = api.plan(api.PlanRequest(**{**BODY, "people": 0, "showers_pp": 0, "laundry_loads": 0, "roof_m2": 0}))
    assert out["result"]["water"] == 0
    assert out["payback"] == "n/a"


def test_generate_uses_a_valid_model_plan_and_reprices():
    good = r.template_blueprint({"roof_m2": 120, "people": 5}, "low", "en").model_dump()
    good["materials"] = [{"item_id": "drip_kit", "quantity": 2, "reason": "Two trees."}]
    out = api.generate(api.GenerateRequest(**BODY, model="fake:1b"), chat=lambda m, p: json.dumps(good))
    assert out["plan"]["source"] == "model" and out["plan"]["notice"] is None
    assert {row["item"] for row in out["plan"]["bom"]} >= {"Drip irrigation kit", "First-flush diverter kit"}
    res = r.simulate(api._profile(api.GenerateRequest(**BODY, model="x"))[0], api.SHARES, api.A)
    assert out["impact"] == pytest.approx(r.impact(res["water"], out["plan"]["cost"], api.A))


def test_generate_falls_back_with_notice_after_bad_output():
    calls = []
    out = api.generate(api.GenerateRequest(**{**BODY, "lang": "ar"}, model="fake:1b"),
                       chat=lambda m, p: calls.append(1) or "Sure! Here is a plan.")
    assert out["plan"]["source"] == "template" and len(calls) == r.MAX_ATTEMPTS
    assert len(out["plan"]["notes"]) == r.MAX_ATTEMPTS and "fake:1b" in out["plan"]["notice"]
    assert out["plan"]["language"] == "ar"


def test_generate_needs_a_model_name():
    with pytest.raises(ValidationError):
        api.GenerateRequest(**BODY, model="")


def test_bad_content_length_is_400_not_a_dropped_connection():
    import http.client
    server = api.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for value in ("abc", "-1"):
            conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            conn.putrequest("POST", "/api/plan")
            conn.putheader("Content-Length", value)
            conn.endheaders()
            assert conn.getresponse().status == 400
    finally:
        server.shutdown()
