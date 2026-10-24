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


# ---------------------------------------------------------------- water balance properties (M1)

import re
import shutil

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as hs

GOVS = rain["governorate"].tolist()
FLOWS = ["start", "inflow", "demand", "met", "shortfall", "overflow", "level"]


def profile_for(gov, roof, cap, people, year, showers=5, laundry=4):
    return r.make_profile(rain, gov, roof, people, showers, laundry, cap, year)


households = dict(gov=hs.sampled_from(GOVS), roof=hs.floats(0, 2000), cap=hs.floats(0, 100),
                  people=hs.integers(0, 30), year=hs.sampled_from(r.YEARS))


@settings(max_examples=300, deadline=None)
@given(**households)
def test_balance_invariants(gov, roof, cap, people, year):
    b = r.simulate(profile_for(gov, roof, cap, people, year), shares, a)["balance"]
    assert not b[FLOWS].isna().any().any()
    assert (b[FLOWS] >= 0).all().all()
    assert (b["level"] <= cap).all()
    assert b["start"].iloc[0] == 0  # tank starts empty in January
    assert b["start"].iloc[1:].tolist() == b["level"].iloc[:-1].tolist()
    lhs, rhs = b["start"] + b["inflow"], b["met"] + b["overflow"] + b["level"]
    assert lhs.tolist() == pytest.approx(rhs.tolist(), rel=1e-12, abs=1e-9)
    assert (b["met"] + b["shortfall"]).tolist() == pytest.approx(b["demand"].tolist())


RAIN_OUTPUTS = ["potential", "rain_used", "water", "overflow"]


@settings(max_examples=200, deadline=None)
@given(gov=households["gov"], roof=households["roof"], cap=households["cap"], people=households["people"])
def test_dry_le_average_le_wet(gov, roof, cap, people):
    res = {y: r.simulate(profile_for(gov, roof, cap, people, y), shares, a) for y in r.YEARS}
    imp = {y: r.impact(res[y]["water"], 100, a) for y in r.YEARS}
    eps = 1e-9
    for key in RAIN_OUTPUTS:
        assert res["dry"][key] <= res["average"][key] + eps <= res["wet"][key] + 2 * eps, key
    for key in ("trips", "jod", "co2"):
        assert imp["dry"][key] <= imp["average"][key] + eps <= imp["wet"][key] + 2 * eps, key
    assert res["dry"]["dry_months"] >= res["average"]["dry_months"] >= res["wet"]["dry_months"]
    inflow = {y: res[y]["balance"]["inflow"].sum() for y in r.YEARS}
    if roof >= 1e-4 and res["average"]["potential"] > 0:  # strict wherever rain reaches the tank (not subnormal roofs)
        assert inflow["dry"] < inflow["average"] < inflow["wet"]


def test_year_multiplier_applied_once():
    p = {**PROFILE, "roof_m2": 100, "rain_mm": 1000, "year": "wet"}
    res = r.simulate(p, shares, a)
    k = a["year_multiplier_wet"]
    assert res["potential"] == pytest.approx(100 * 1.0 * k * a["runoff_coefficient"])
    assert res["balance"]["inflow"].sum() == pytest.approx(res["potential"] * (1 - a["first_flush_loss"]))


def test_harvest_is_one_litre_per_mm_per_m2():
    b = bal(roof_m2=1, rain_m=0.001, shares=[1] + [0] * 11, runoff=1.0, demand_m3=[0.0] * 12, capacity_m3=10)
    assert b["inflow"].iloc[0] * r.LITRES_PER_M3 == pytest.approx(1.0)


def test_demand_uses_real_days_per_month():
    res = r.simulate({**PROFILE, "people": 2}, shares, a)
    litres = res["balance"]["demand"] * r.LITRES_PER_M3
    expected = [2 * a["nonpotable_litres_per_person_day"] * d for d in r.DAYS_IN_MONTH]
    assert litres.tolist() == pytest.approx(expected)
    assert sum(r.DAYS_IN_MONTH) == 365


@pytest.mark.parametrize("change", [{"roof_m2": 0}, {"capacity_m3": 0}, {"people": 0},
                                    {"roof_m2": 0, "people": 0, "laundry_loads": 0, "showers_pp": 0}])
def test_zero_inputs_give_zeros_not_errors(change):
    res = r.simulate({**PROFILE, **change}, shares, a)
    assert not res["balance"][FLOWS].isna().any().any()
    for key in ("potential", "rain_used", "greywater", "water", "overflow"):
        assert res[key] >= 0 and res[key] == res[key]
    imp = r.impact(res["water"], 300, a)
    assert all(v is None or v >= 0 for v in imp.values())


def test_all_zero_household_payback_na():
    res = r.simulate({**PROFILE, "roof_m2": 0, "people": 0, "laundry_loads": 0}, shares, a)
    assert res["water"] == 0
    imp = r.impact(res["water"], 300, a)
    assert imp["payback_months"] is None and r.format_payback(imp["payback_months"]) == "n/a"


@pytest.mark.parametrize("bad", [{"roof_m2": -1}, {"people": -1}, {"capacity_m3": float("nan")},
                                 {"year": "normal"}, {"roof_m2": float("inf")}, {"extra": 1}, {"people": 2.5}])
def test_bad_inputs_raise_input_error(bad):
    with pytest.raises(r.InputError):
        r.simulate({**PROFILE, **bad}, shares, a)


def test_unknown_governorate_rejected():
    with pytest.raises(r.InputError):
        profile_for("Atlantis", 100, 2, 4, "average")


# ---------------------------------------------------------------- greywater (M2)

def test_laundry_is_per_household_showers_per_person():
    g = lambda people, showers, laundry: r.greywater_week(people, showers, laundry, a)
    rec = a["greywater_recovery"] / r.LITRES_PER_M3
    assert g(2, 0, 3) - g(1, 0, 3) == pytest.approx(a["sink_litres_per_person_week"] * rec)
    assert g(1, 0, 4) - g(1, 0, 3) == pytest.approx(a["litres_per_laundry_load"] * rec)
    assert g(3, 2, 0) - g(3, 1, 0) == pytest.approx(3 * a["litres_per_shower"] * rec)


def test_greywater_annual_is_52_weeks():
    res = r.simulate(PROFILE, shares, a)
    week = r.greywater_week(PROFILE["people"], PROFILE["showers_pp"], PROFILE["laundry_loads"], a)
    assert res["greywater"] == pytest.approx(week * 52)


FORBIDDEN_SOURCES = re.compile(r"kitchen|toilet|blackwater|black water|dishwasher|مطبخ|مرحاض|مراحيض|مجلى|جلاية")


def test_no_kitchen_or_toilet_source_anywhere():
    import inspect
    assert not FORBIDDEN_SOURCES.search(inspect.getsource(r.greywater_week).lower())
    assert not FORBIDDEN_SOURCES.search(catalog.to_csv(index=False).lower())
    gw_params = [p for p in a if "shower" in p or "laundry" in p or "sink" in p or "greywater" in p]
    assert not any(FORBIDDEN_SOURCES.search(p) for p in gw_params)
    for budget in r.BUDGETS:
        for lang in ("en", "ar"):
            prompt = r.build_prompt(PROFILE, r.simulate(PROFILE, shares, a), catalog, plants, budget, lang)
            assert not FORBIDDEN_SOURCES.search(prompt.lower())


# ---------------------------------------------------------------- impact (M3, M4, S2)

def test_impact_formulas():
    imp = r.impact(10, 120, a)
    trips = 10 * a["tanker_share"] / a["tanker_volume"]
    assert imp["trips"] == pytest.approx(trips)
    assert imp["jod"] == pytest.approx(trips * a["tanker_price"] + 10 * (1 - a["tanker_share"]) * a["municipal_tariff"])
    assert imp["co2"] == pytest.approx(trips * a["diesel_per_trip"] * a["diesel_co2"]
                                       + 10 * a["pump_energy"] * a["grid_co2"])
    assert imp["payback_months"] == pytest.approx(12 * 120 / imp["jod"])


def test_trips_are_fractional_not_floored():
    assert r.impact(a["tanker_volume"] / a["tanker_share"] / 2, 0, a)["trips"] == pytest.approx(0.5)


@pytest.mark.parametrize("water", [0, 0.0, -1])
def test_payback_na_when_nothing_saved(water):
    p = r.impact(water, 500, a)["payback_months"]
    assert p is None and r.format_payback(p) == "n/a"


def test_zero_cost_payback_is_zero_months_not_na():
    assert r.format_payback(r.impact(10, 0, a)["payback_months"]) == "0 months"


def test_pre_generation_payback_uses_template_cost():
    for budget in r.BUDGETS:
        bp = r.template_blueprint(PROFILE, budget, "en")
        cost = r.plan_cost(r.price(bp, catalog))
        assert cost > 0
    assert (r.plan_cost(r.price(r.template_blueprint(PROFILE, "full", "en"), catalog))
            > r.plan_cost(r.price(r.template_blueprint(PROFILE, "low", "en"), catalog)))


def test_sareef_signs_and_consistency():
    res = r.simulate(PROFILE, shares, a)
    imp = r.impact(res["water"], 0, a)
    on, off = r.sareef(res, a, True), r.sareef(res, a, False)
    for k in ("trips", "jod", "co2"):
        assert on["delta"][k] <= 0
        assert on["delta"][k] == pytest.approx(-imp[k])
        assert on["before"][k] == pytest.approx(on["now"][k] + imp[k])
        assert off["now"][k] == off["before"][k] == on["before"][k]
        assert on["now"][k] >= 0
    assert off["delta"] is None


def test_community_scales_linearly():
    res = r.simulate(PROFILE, shares, a)
    imp = r.impact(res["water"], 100, a)
    one = r.community(res, imp, 1)
    for homes in (1, 7, 250, 1000):
        c = r.community(res, imp, homes)
        assert c["water"] == pytest.approx(one["water"] * homes)
        assert c["trips"] == pytest.approx(one["trips"] * homes)
        assert c["co2_t"] == pytest.approx(imp["co2"] * homes / 1000)
    assert f"{r.community(res, imp, 1000)['water']:,.0f}" == f"{res['water'] * 1000:,.0f}"
    for bad in (0, 1001, 2.0, True):
        with pytest.raises(r.InputError):
            r.community(res, imp, bad)


# ---------------------------------------------------------------- data loading (M11)

def broken_copy(tmp_path, name, edit):
    for f in r.DATA.glob("*.csv"):
        shutil.copy(f, tmp_path / f.name)
    df = pd.read_csv(tmp_path / name, dtype=str, keep_default_na=False)
    edit(df).to_csv(tmp_path / name, index=False)
    return tmp_path


@pytest.mark.parametrize("name,edit,match", [
    ("rainfall.csv", lambda d: d.drop(columns="annual_mm"), "missing column"),
    ("rainfall.csv", lambda d: d.drop(columns="status"), "missing column"),
    ("rainfall.csv", lambda d: d.assign(annual_mm=d["annual_mm"].where(d.index != 2, "4o0")), "line 4"),
    ("rainfall.csv", lambda d: d.assign(annual_mm=d["annual_mm"].where(d.index != 0, "-5")), "annual_mm"),
    ("rainfall.csv", lambda d: pd.concat([d, d.iloc[[0]]]), "duplicate"),
    ("monthly_share.csv", lambda d: d.assign(share_of_annual_rain=d["share_of_annual_rain"].where(
        d["month"] != "Jan", "0.30")), "sum to"),
    ("monthly_share.csv", lambda d: d[d["month"] != "Jul"], "months"),
    ("catalog.csv", lambda d: d[d["item_id"] != "first_flush"], "required safety"),
    ("catalog.csv", lambda d: d.assign(budget_level=d["budget_level"].replace("full", "premium")), "budget_level"),
    ("catalog.csv", lambda d: d.assign(price_jod=d["price_jod"].where(d.index != 0, "")), "price_jod"),
    ("plants.csv", lambda d: d.assign(greywater_ok=d["greywater_ok"].replace("false", "no")), "greywater_ok"),
    ("assumptions.csv", lambda d: d[d["parameter"] != "tanker_price"], "tanker_price"),
    ("assumptions.csv", lambda d: d.assign(value=d["value"].where(d["parameter"] != "runoff_coefficient", "1.5")),
     "fraction"),
    ("assumptions.csv", lambda d: d.assign(value=d["value"].where(d["parameter"] != "tanker_volume", "0")),
     "tanker_volume"),
    ("assumptions.csv", lambda d: d.assign(value=d["value"].where(d["parameter"] != "year_multiplier_wet", "0.5")),
     "year multipliers"),
])
def test_loader_fails_loudly(tmp_path, name, edit, match):
    with pytest.raises(r.DataError, match=match):
        r.load_tables(broken_copy(tmp_path, name, edit))


def test_missing_file_is_data_error(tmp_path):
    with pytest.raises(r.DataError, match="cannot read"):
        r.load_tables(tmp_path)


def test_every_table_has_source_and_status():
    for name, cols in r.COLUMNS.items():
        assert {"source", "status"} <= set(cols), name


def test_every_assumption_used_in_code_is_in_csv():
    import inspect
    used = set(re.findall(r'a\["(\w+)"\]', inspect.getsource(r)))
    used |= {f"year_multiplier_{y}" for y in r.YEARS}
    assert used <= set(assumptions["parameter"])
    assert set(r.PARAMETERS) <= set(assumptions["parameter"])
