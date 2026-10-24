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
    assert opts["limits"]["people"] == (1, 12)


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


@pytest.mark.parametrize("bad", [{"people": 0}, {"roof_m2": 401}, {"capacity_m3": 0}, {"governorate": "Paris"},
                                 {"budget": "gold"}, {"lang": "fr"}])
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
