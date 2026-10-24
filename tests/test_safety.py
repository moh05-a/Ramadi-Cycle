"""Safety layer: fixed warnings, disclaimer and first-flush on every plan in both languages, model or template;
the banned-term scan applies to model text only; badge counts match the rules applied."""
import json

import pytest

import api
import ramadi as r
from conftest import PROFILE

BODY = {"governorate": "Irbid", "roof_m2": 120, "people": 5, "showers_pp": 5, "laundry_loads": 4,
        "capacity_m3": 2.0, "budget": "low"}
FIRST_FLUSH = {"en": "First-flush diverter kit", "ar": "محوّل مياه الدفقة الأولى"}

MODEL_PLAN = {
    "en": {"language": "en", "summary": "A small system.", "rainwater_steps": ["Fit gutters.", "Fit the diverter.", "Set the tank."],
           "greywater_steps": ["Fit the valve.", "Fit the filter.", "Lay the drip line."],
           "materials": [{"item_id": "drip_kit", "quantity": 1, "reason": "Trees."}], "plants": []},
    "ar": {"language": "ar", "summary": "نظام صغير.", "rainwater_steps": ["ركّب المزاريب.", "ركّب المحوّل.", "ثبّت الخزان."],
           "greywater_steps": ["ركّب المحبس.", "ركّب الفلتر.", "مدّ خط التنقيط."],
           "materials": [{"item_id": "drip_kit", "quantity": 1, "reason": "للأشجار."}], "plants": []},
}


def plans(lang):
    """The template plan and a model plan that leaves out every required part."""
    template = api.plan(api.PlanRequest(**BODY, lang=lang))
    model = api.generate(api.GenerateRequest(**BODY, lang=lang, model="fake"), chat=lambda m, p: json.dumps(MODEL_PLAN[lang]))
    assert template["plan"]["source"] == "template" and model["plan"]["source"] == "model"
    return {"template": template, "model": model}


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("kind", ["template", "model"])
def test_every_plan_carries_all_warnings_disclaimer_and_first_flush(lang, kind):
    out = plans(lang)[kind]
    md = out["markdown"]
    assert len(r.WARNINGS[lang]) == 6 and all(w in md for w in r.WARNINGS[lang])
    assert r.DISCLAIMER[lang] in md
    assert FIRST_FLUSH[lang] in {row["item"] for row in out["plan"]["bom"]}
    assert all(c["passed"] for c in out["plan"]["checks"])


def test_fixed_warnings_name_the_banned_sources_but_are_never_scanned():
    # The warnings must say "toilet", "kitchen" and "bleach"; scanning them would reject every plan.
    assert all(r.find_banned(w) for w in r.WARNINGS["en"][:2])
    tpl = r.template_blueprint(PROFILE, "low", "en")
    tables = r.load_tables()
    assert r.validate(tpl.model_dump_json(), tables.catalog, tables.plants, "low")[1] is None


@pytest.mark.parametrize("text", ["Use kitchen sink water too.", "Pipe toilet water to the trees.", "Add a cup of bleach.",
                                  "Rinse with chlorine.", "أضف الكلور للماء.", "استخدم مياه المطبخ."])
def test_banned_scan_flags_model_text(text):
    assert r.find_banned(text)


def test_badge_count_matches_rules_applied():
    out = plans("en")["model"]
    assert len(out["plan"]["checks"]) == len(r.safety_checks(r.template_blueprint(PROFILE, "low", "en")))


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_garden_carries_the_greywater_rules_in_its_language(lang):
    out = api.garden(api.GardenRequest(**BODY, lang=lang))
    assert out["warnings"] == [r.WARNINGS[lang][i] for i in r.GARDEN_WARNINGS]
    # the four greywater rules: sources, cleaners, raw-eaten crops, storage time
    assert len(out["warnings"]) == 4
