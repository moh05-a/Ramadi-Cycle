"""Garden planner: water maths, the checks a model's garden must pass, the feedback loop and the API route."""
import json
import shutil

import pandas as pd
import pytest
from pydantic import ValidationError

import api
import ramadi as r
from conftest import PROFILE


@pytest.fixture(scope="module")
def garden(tables):
    return r.load_garden(tables.rain, tables.plants)


@pytest.fixture(scope="module")
def ctx(tables, a, garden):
    res = r.simulate(PROFILE, tables.shares, a)
    return r.garden_context(PROFILE, res, tables.shares, a, garden, 40)


def plan(**over):
    base = {"language": "en", "summary": "Two fruit trees and a herb border.",
            "plants": [{"plant_id": "olive", "count": 1, "reason": "Shade by the wall."},
                       {"plant_id": "rosemary", "count": 3, "reason": "Low border."}],
            "care_steps": ["Plant in November.", "Mulch 10 cm deep.", "Check the drippers monthly."]}
    return json.dumps(base | over)


def check(raw, ctx, garden, tables, lang="en"):
    return r.validate_garden(raw, ctx, garden, tables.plants, lang)


# ---------------------------------------------------------------- data and maths

def test_garden_tables_cover_every_governorate_and_only_greywater_safe_plants(tables, garden):
    assert set(tables.rain["governorate"]) <= set(garden.et0.index)
    safe = set(tables.plants.loc[tables.plants["greywater_ok"], "plant_id"])
    assert set(garden.plants.index) <= safe


def test_garden_plant_must_be_greywater_safe(tmp_path, tables):
    for name in ("et0.csv", "garden_plants.csv", "humidity.csv", "soil.csv"):
        shutil.copy(r.DATA / name, tmp_path / name)
    gp = pd.read_csv(tmp_path / "garden_plants.csv", dtype=str)
    gp.loc[0, "plant_id"] = "mint"  # eaten raw, greywater_ok false
    gp.to_csv(tmp_path / "garden_plants.csv", index=False)
    with pytest.raises(r.DataError, match="mint"):
        r.load_garden(tables.rain, tables.plants, tmp_path)


def test_humidity_and_soil_cover_every_governorate_with_sane_values(tables, garden):
    govs = set(tables.rain["governorate"])
    assert govs <= set(garden.humidity.index) and govs <= set(garden.soil.index)
    assert ((garden.humidity[r.MONTHS] > 0) & (garden.humidity[r.MONTHS] <= 100)).all().all()
    soil = garden.soil
    assert ((soil["sand_pct"] + soil["silt_pct"] + soil["clay_pct"]).between(97, 103)).all()
    assert soil["ph"].between(4, 10).all() and set(soil["texture"]) <= set(r.SOIL_GROUPS)


@pytest.mark.parametrize("texture, group", [("sand", "sandy"), ("loam", "loamy"), ("silty clay", "clayey"), ("odd", "loamy")])
def test_watering_note_follows_soil_texture(texture, group):
    assert r.watering_note(texture, "en") == r.WATERING_NOTE[group]["en"]


@pytest.mark.parametrize("p, expected", [(0, 0), (10, 0), (50, 20), (70, 32), (100, 56)])
def test_effective_rain_matches_fao_formula_and_is_continuous(p, expected):
    assert r.effective_rain(p) == pytest.approx(expected)


def test_plant_need_is_et0_times_kc_times_canopy_over_efficiency():
    row = {"kc_ini": 0.5, "kc_mid": 1.0, "kc_end": 0.5, "deciduous": False, "canopy_m2": 2.0}
    need = r.plant_need(row, [100.0] * 12, [0.0] * 12, 0.5)
    assert need[6] == pytest.approx(100 * 1.0 * 2 / 0.5)  # July is mid-season
    assert need[0] == pytest.approx(100 * 0.5 * 2 / 0.5)  # evergreen keeps kc_ini in winter


def test_deciduous_plants_need_nothing_in_deep_winter():
    row = {"kc_ini": 0.5, "kc_mid": 1.0, "kc_end": 0.5, "deciduous": True, "canopy_m2": 2.0}
    need = r.plant_need(row, [100.0] * 12, [0.0] * 12, 1.0)
    assert need[0] == need[1] == need[11] == 0


def test_supply_is_greywater_every_month_plus_tank_overflow(tables, a, ctx):
    res = r.simulate(PROFILE, tables.shares, a)
    grey_day = res["greywater"] / 52 / 7 * 1000
    for m, (days, over) in enumerate(zip(r.DAYS_IN_MONTH, res["balance"]["overflow"])):
        assert ctx["supply"][m] == pytest.approx(grey_day * days + over * 1000)


def test_summer_need_exceeds_winter_need(ctx):
    assert ctx["need"]["olive"][6] > ctx["need"]["olive"][0]


@pytest.mark.parametrize("m2", [0, -5, r.GARDEN_M2_MAX + 1, True])
def test_garden_area_must_be_in_range(tables, a, garden, m2):
    res = r.simulate(PROFILE, tables.shares, a)
    with pytest.raises(r.InputError):
        r.garden_context(PROFILE, res, tables.shares, a, garden, m2)


# ---------------------------------------------------------------- validation

def test_valid_garden_passes(ctx, garden, tables):
    gp, why = check(plan(), ctx, garden, tables)
    assert why is None and [p.plant_id for p in gp.plants] == ["olive", "rosemary"]


@pytest.mark.parametrize("over, code", [
    ({"plants": [{"plant_id": "mint", "count": 1, "reason": "x"}]}, r.PLANT_NOT_GREYWATER_SAFE),
    ({"plants": [{"plant_id": "baobab", "count": 1, "reason": "x"}]}, r.UNKNOWN_PLANT),
    ({"plants": [{"plant_id": "olive", "count": 0, "reason": "x"}]}, r.BAD_QUANTITY),
    ({"plants": [{"plant_id": "olive", "count": 21, "reason": "x"}]}, r.BAD_QUANTITY),
    ({"plants": []}, r.EMPTY_GARDEN),
    ({"plants": [{"plant_id": "olive", "count": 1, "reason": "x"}] * 2}, r.DUPLICATE_PLANT),
    ({"plants": [{"plant_id": "olive", "count": 4, "reason": "x"}]}, r.GARDEN_TOO_BIG),
    ({"plants": [{"plant_id": "rosemary", "count": 1, "reason": "Not for drinking water."}]}, r.BANNED_TERM),
    ({"care_steps": ["One."]}, r.SCHEMA),
    ({"care_steps": ["One.", "Two.", "Three.", "Four."]}, r.SCHEMA),
    ({"plants": [{"plant_id": p, "count": 1, "reason": "x"} for p in
                 ["rosemary", "lavender", "bougainvillea", "olive", "fig", "lemon", "grape"]]}, r.SCHEMA),
    ({"language": "ar"}, r.WRONG_LANGUAGE),
    ({"extra": 1}, r.SCHEMA),
])
def test_bad_gardens_are_rejected(over, code, ctx, garden, tables):
    gp, why = check(plan(**over), ctx, garden, tables)
    assert gp is None and why.code == code


def test_garden_that_runs_dry_in_summer_is_rejected_with_the_month(ctx, garden, tables):
    thirsty = {"plants": [{"plant_id": "pistachio", "count": 2, "reason": "x"}, {"plant_id": "almond", "count": 1, "reason": "x"}]}
    gp, why = r.validate_garden(plan(**thirsty), dict(ctx, garden_m2=200), garden, tables.plants, "en")
    assert gp is None and why.code == r.GARDEN_SHORT
    assert "L/week" in why.detail and why.detail.split()[0] in r.MONTHS[4:9]


def test_prose_and_empty_replies_are_rejected(ctx, garden, tables):
    assert check("Here is your garden!", ctx, garden, tables)[1].code == r.NOT_JSON
    assert check("", ctx, garden, tables)[1].code == r.EMPTY_RESPONSE


# ---------------------------------------------------------------- model loop

def test_model_garden_is_used_when_it_passes(ctx, garden, tables):
    gen = r.generate_garden(ctx, garden, tables.plants, "en", "fake", chat=lambda m, p, s: plan())
    assert gen.source == "model" and gen.trace == [{"attempt": 1, "outcome": "passed", "code": "", "detail": ""}]


def test_rejection_reason_goes_back_to_the_model(ctx, garden, tables):
    prompts = []
    replies = iter([plan(plants=[{"plant_id": "olive", "count": 4, "reason": "x"}]), plan()])

    def chat(model, prompt, schema):
        prompts.append(prompt)
        assert schema == r.GardenPlan.model_json_schema()
        return next(replies)

    gen = r.generate_garden(ctx, garden, tables.plants, "en", "fake", chat=chat)
    assert gen.source == "model" and [t["outcome"] for t in gen.trace] == ["rejected", "passed"]
    assert "rejected" not in prompts[0] and "50 m² but the garden is 40 m²" in prompts[1]


def test_falls_back_to_template_after_max_attempts(ctx, garden, tables):
    calls = []
    gen = r.generate_garden(ctx, garden, tables.plants, "ar", "fake", chat=lambda m, p, s: calls.append(1) or "prose")
    assert gen.source == "none" and gen.plan is None and len(calls) == r.MAX_ATTEMPTS
    assert r.garden_notice(gen, "fake", "en").startswith("fake could not")


def test_transport_error_stops_at_once(ctx, garden, tables):
    calls = []

    def down(model, prompt, schema):
        calls.append(1)
        raise r.ModelUnavailable("connection refused")

    gen = r.generate_garden(ctx, garden, tables.plants, "en", "fake", chat=down)
    assert gen.source == "none" and gen.plan is None and len(calls) == 1 and gen.trace[0]["outcome"] == "error"


def test_no_model_means_no_plants_and_no_call(ctx, garden, tables):
    gen = r.generate_garden(ctx, garden, tables.plants, "en", "", chat=lambda *x: pytest.fail("called"))
    assert gen.source == "none" and gen.plan is None and gen.trace == []


def test_prompt_puts_fixed_text_first_and_household_last(ctx, garden):
    prompt = r.build_garden_prompt(ctx, garden, "en", "shade\nfor the kids")
    assert prompt.index("plant_id m2 L/week") < prompt.index("Soil:") < prompt.index("Water budget:") \
        < prompt.index("Wishes: shade for the kids")
    assert "kitchen" not in prompt.lower() and "toilet" not in prompt.lower()


def test_prompt_budget_is_the_driest_week_and_each_plant_its_peak(ctx, garden):
    prompt = r.build_garden_prompt(ctx, garden, "en")
    assert f"Water budget: {r.budget_week(ctx):.0f} L/week" in prompt
    assert f"\nolive 12.6 {r.peak_week(ctx['need']['olive']):.0f}\n" in prompt


def test_prompt_carries_soil_and_humidity(ctx, garden):
    soil = garden.soil.loc[PROFILE["governorate"]]
    prompt = r.build_garden_prompt(ctx, garden, "en")
    assert f"Soil: {soil['texture']}, pH {soil['ph']:g}" in prompt
    assert f"{garden.humidity.loc[PROFILE['governorate'], 'Jul']:.0f}% in July" in prompt


def test_prompt_stays_short(ctx, garden):
    # Every token costs time on a CPU; the household part must not grow the fixed prompt much.
    assert len(r.build_garden_prompt(ctx, garden, "ar", "x" * r.WISHES_MAX)) < 1300


def test_shared_prefix_is_identical_for_two_households_in_one_governorate(tables, a, garden, ctx):
    other = dict(PROFILE, people=8, laundry_loads=6)
    res = r.simulate(other, tables.shares, a)
    ctx2 = r.garden_context(other, res, tables.shares, a, garden, 60)
    p1, p2 = r.build_garden_prompt(ctx, garden, "en"), r.build_garden_prompt(ctx2, garden, "en")
    assert p1.split("Water budget:")[0] == p2.split("Water budget:")[0]


# ---------------------------------------------------------------- API

BODY = {"governorate": "Irbid", "roof_m2": 120, "people": 5, "showers_pp": 5, "laundry_loads": 4,
        "capacity_m3": 2.0, "budget": "low", "lang": "en"}


def test_api_garden_without_model_gives_site_and_water_but_no_plants():
    out = api.garden(api.GardenRequest(**BODY))
    assert out["source"] == "none" and out["plan"] is None and out["notice"]
    assert len(out["supply_l_week"]) == 12 and out["site"]["soil"]["texture"]


def test_api_garden_after_failed_model_shows_no_plants():
    out = api.garden(api.GardenRequest(**BODY, model="fake:1b"), chat=lambda m, p, s: "prose")
    assert out["plan"] is None and len(out["trace"]) == r.MAX_ATTEMPTS and "fake:1b" in out["notice"]


def test_api_model_garden_numbers_add_up():
    out = api.garden(api.GardenRequest(**BODY, model="fake:1b"), chat=lambda m, p, s: plan())
    g = out["plan"]
    assert all(d <= s + 1e-6 for d, s in zip(g["demand_l_week"], out["supply_l_week"]))
    assert g["area_used"] <= out["garden_m2"] and all(c["passed"] for c in g["checks"])


def test_template_build_plan_suggests_no_plants():
    for lang in ("en", "ar"):
        bp = r.template_blueprint(PROFILE, "low", lang)
        assert bp.plants == [] and "## Plants" not in r.to_markdown(bp, r.price(bp, api.CATALOG), PROFILE, {"water": 1})


def test_api_garden_uses_model_design_and_flags_salt_sensitive_plants():
    reply = plan(plants=[{"plant_id": "lemon", "count": 1, "reason": "Fresh lemons."}])
    out = api.garden(api.GardenRequest(**BODY, model="fake:1b", wishes="lemons"), chat=lambda m, p, s: reply)
    assert out["source"] == "model" and out["notice"] is None
    assert out["plan"]["plants"][0]["name"] == "Lemon tree" and out["plan"]["plants"][0]["salt_note"]
    assert out["site"]["soil"]["texture"] in r.SOIL_GROUPS and len(out["site"]["humidity"]) == 12
    assert out["site"]["watering_note"] == r.watering_note(out["site"]["soil"]["texture"], "en")


@pytest.mark.parametrize("bad", [{"garden_m2": 0}, {"garden_m2": r.GARDEN_M2_MAX + 1}, {"wishes": "x" * (r.WISHES_MAX + 1)}])
def test_api_garden_rejects_bad_input(bad):
    with pytest.raises(ValidationError):
        api.GardenRequest(**BODY, **bad)


def test_options_carry_garden_tables_and_limits():
    opts = api.options()
    assert {"garden_plants", "et0", "humidity", "soil"} <= set(opts["tables"]) and opts["garden"]["garden_m2"] == [1, r.GARDEN_M2_MAX]
