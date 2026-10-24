import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import ramadi as r

rain, shares, catalog, plants, assumptions = r.load_tables()
a = r.assumption_values(assumptions)
PROFILE = {"governorate": "Irbid", "rain_mm": 470, "roof_m2": 120, "people": 5, "showers_pp": 5,
           "laundry_loads": 4, "capacity_m3": 2.0, "year": "average"}


def bal(**kw):
    args = dict(roof_m2=100, rain_m=0.5, shares=shares, k=1.0, runoff=0.85, first_flush=0.0,
                capacity_m3=2.0, demand_m3=[1.0] * 12)
    return r.water_balance(**{**args, **kw})


# ---------------------------------------------------------------- engine

def test_annual_potential():
    assert r.annual_potential(100, 0.5, 0.85) == pytest.approx(42.5)


def test_shares_sum_to_one():
    assert sum(shares) == pytest.approx(1.0)


def test_zero_roof():
    res = r.simulate({**PROFILE, "roof_m2": 0, "showers_pp": 0, "laundry_loads": 0, "people": 1}, shares,
                     {**a, "sink_litres_per_person_week": 0})
    assert res["balance"]["inflow"].sum() == 0
    assert res["water"] == 0
    assert r.impact(0, 100, a)["payback_months"] is None


def test_tank_cap():
    b = bal(capacity_m3=1.0, demand_m3=[0.0] * 12)
    assert (b["level"] <= 1.0).all()
    assert b["overflow"].sum() == pytest.approx(b["inflow"].sum() - 1.0)


def test_shortfall_never_negative():
    b = bal(roof_m2=10, demand_m3=[5.0] * 12)
    assert (b["shortfall"] >= 0).all() and (b["level"] >= 0).all()
    assert (b["met"] + b["shortfall"]).tolist() == pytest.approx([5.0] * 12)


def test_year_type_order():
    w = {y: r.simulate({**PROFILE, "year": y}, shares, a)["balance"]["inflow"].sum() for y in ("dry", "average", "wet")}
    assert w["dry"] < w["average"] < w["wet"]


def test_mass_balance():
    b = bal()
    assert b["inflow"].sum() == pytest.approx(b["met"].sum() + b["overflow"].sum() + b["level"].iloc[-1])


# ---------------------------------------------------------------- guardrails

def good_plan(**overrides):
    plan = r.template_blueprint(PROFILE, "low", "en").model_dump()
    plan.update(overrides)
    return json.dumps(plan)


def test_template_passes_own_validation():
    for budget in ("low", "full"):
        for lang in ("en", "ar"):
            raw = r.template_blueprint(PROFILE, budget, lang).model_dump_json()
            bp, why = r.validate(raw, catalog, plants, budget)
            assert bp and why is None, why


def test_unknown_item_rejected():
    raw = good_plan(materials=[{"item_id": "gold_tap", "quantity": 1, "reason": "x"}])
    assert r.validate(raw, catalog, plants, "low")[0] is None


def test_out_of_budget_item_rejected():
    raw = good_plan(materials=[{"item_id": "transfer_pump", "quantity": 1, "reason": "x"}])
    assert r.validate(raw, catalog, plants, "low")[0] is None


def test_raw_eaten_plant_rejected():
    raw = good_plan(plants=[{"plant_id": "lettuce", "reason": "x"}])
    assert r.validate(raw, catalog, plants, "low")[0] is None


def test_quantity_limit():
    raw = good_plan(materials=[{"item_id": "gutter_pvc", "quantity": 500, "reason": "x"}])
    assert r.validate(raw, catalog, plants, "low")[0] is None


@pytest.mark.parametrize("text", ["Add bleach weekly to keep it clean.", "Safe for drinking after filtering.",
                                  "يمكن استخدامها للشرب"])
def test_banned_term_rejected(text):
    raw = good_plan(summary=text)
    bp, why = r.validate(raw, catalog, plants, "low")
    assert bp is None and why.code == r.BANNED_TERM


def test_required_items_added():
    raw = good_plan(materials=[{"item_id": "drip_kit", "quantity": 1, "reason": "x"}])
    bp, _ = r.validate(raw, catalog, plants, "low")
    assert {"first_flush", "label_kit"} <= {m.item_id for m in bp.materials}


def test_invalid_json_retries_then_template():
    calls = []
    def prose(model, prompt):
        calls.append(1)
        return "Sure! Here is your plan: buy a tank."
    res = r.simulate(PROFILE, shares, a)
    bp, source, notes = r.generate(PROFILE, res, catalog, plants, "low", "en", "fake", chat=prose)
    assert source == "template" and len(calls) == 3 and len(notes) == 3


def test_valid_model_output_used():
    res = r.simulate(PROFILE, shares, a)
    bp, source, _ = r.generate(PROFILE, res, catalog, plants, "low", "en", "fake", chat=lambda m, p: good_plan())
    assert source == "model"


def test_disclaimers_present_in_download():
    for lang in ("en", "ar"):
        bp = r.template_blueprint(PROFILE, "full", lang)
        md = r.to_markdown(bp, r.price(bp, catalog), PROFILE, r.simulate(PROFILE, shares, a))
        assert r.DISCLAIMER[lang] in md and all(w in md for w in r.WARNINGS[lang])
        assert all(ok for _, ok in r.safety_checks(bp))
