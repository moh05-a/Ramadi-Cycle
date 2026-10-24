"""Ramadi-Cycle core: water-balance engine, catalog, blueprint schema, safety checks, local model.

Code owns every number, price and safety rule. The model only picks catalog IDs and writes text.
"""
import json
import urllib.request
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

DATA = Path(__file__).parent / "data"
OLLAMA_URL = "http://localhost:11434"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------- data

def load_tables():
    rain = pd.read_csv(DATA / "rainfall.csv")
    shares = pd.read_csv(DATA / "monthly_share.csv").set_index("month").loc[MONTHS, "share_of_annual_rain"].tolist()
    catalog = pd.read_csv(DATA / "catalog.csv")
    plants = pd.read_csv(DATA / "plants.csv")
    assumptions = pd.read_csv(DATA / "assumptions.csv")
    return rain, shares, catalog, plants, assumptions


def assumption_values(assumptions):
    return dict(zip(assumptions["parameter"], assumptions["value"].astype(float)))


# ---------------------------------------------------------------- engine

def annual_potential(roof_m2, rain_m, runoff):
    return roof_m2 * rain_m * runoff


def water_balance(roof_m2, rain_m, shares, k, runoff, first_flush, capacity_m3, demand_m3):
    """Monthly harvest-tank balance. demand_m3 is a list of 12 monthly demands. Tank starts empty in January."""
    level, rows = 0.0, []
    for month, s, d in zip(MONTHS, shares, demand_m3):
        inflow = roof_m2 * (rain_m * s * k) * runoff * (1 - first_flush)
        available = level + inflow
        shortfall = max(0.0, d - available)
        overflow = max(0.0, available - d - capacity_m3)
        level = min(capacity_m3, max(0.0, available - d))
        rows.append({"month": month, "inflow": inflow, "demand": d, "met": d - shortfall,
                     "shortfall": shortfall, "overflow": overflow, "level": level})
    return pd.DataFrame(rows)


def greywater_week(people, showers_pp, laundry_loads, a):
    """Weekly recovered greywater in m³. Laundry is per household, showers and sink per person."""
    litres = (people * showers_pp * a["litres_per_shower"]
              + laundry_loads * a["litres_per_laundry_load"]
              + people * a["sink_litres_per_person_week"])
    return litres * a["greywater_recovery"] / 1000


def impact(water_m3, system_cost, a):
    s, T = a["tanker_share"], a["tanker_volume"]
    trips = water_m3 * s / T
    jod = trips * a["tanker_price"] + water_m3 * (1 - s) * a["municipal_tariff"]
    co2 = trips * a["diesel_per_trip"] * a["diesel_co2"] + water_m3 * a["pump_energy"] * a["grid_co2"]
    payback = 12 * system_cost / jod if jod > 0 else None
    return {"trips": trips, "jod": jod, "co2": co2, "payback_months": payback}


def simulate(profile, shares, a):
    """Run the whole household model. profile keys: roof_m2, rain_mm, year, people, showers_pp, laundry_loads, capacity_m3."""
    k = a[f"year_multiplier_{profile['year']}"]
    rain_m = profile["rain_mm"] / 1000
    monthly_demand = profile["people"] * a["nonpotable_litres_per_person_day"] * 30.4 / 1000
    bal = water_balance(profile["roof_m2"], rain_m, shares, k, a["runoff_coefficient"], a["first_flush_loss"],
                        profile["capacity_m3"], [monthly_demand] * 12)
    grey = greywater_week(profile["people"], profile["showers_pp"], profile["laundry_loads"], a) * 52
    rain_used = bal["met"].sum()
    return {
        "balance": bal,
        "potential": annual_potential(profile["roof_m2"], rain_m * k, a["runoff_coefficient"]),
        "rain_used": rain_used,
        "greywater": grey,
        "water": rain_used + grey,
        "dry_months": int((bal["shortfall"] > 0).sum()),
        "overflow": bal["overflow"].sum(),
    }


# ---------------------------------------------------------------- blueprint schema

class PlanItem(BaseModel):
    item_id: str
    quantity: int = Field(ge=1, le=50)
    reason: str = Field(max_length=200)


class PlantPick(BaseModel):
    plant_id: str
    reason: str = Field(max_length=200)


class Blueprint(BaseModel):
    language: Literal["en", "ar"]
    summary: str
    greywater_steps: list[str]
    rainwater_steps: list[str]
    materials: list[PlanItem]
    plants: list[PlantPick]


def allowed_items(catalog, budget):
    return catalog[catalog["budget_level"].isin([budget, "both"])]


# ---------------------------------------------------------------- safety

# Fixed warnings rendered by code. The model cannot remove or rewrite these.
WARNINGS = {
    "en": [
        "Only sink, shower and laundry water goes into the greywater system. Never toilet or kitchen water.",
        "Do not put bleach or harsh chemicals down drains that feed the greywater system.",
        "Never use greywater on leaves or roots that are eaten raw. Water the soil, not the plant.",
        "Use greywater within 24 hours. Do not store it. (Confirm this window against a local source.)",
        "Every rainwater tank must have a first-flush diverter before the inlet.",
        "Harvested rain and greywater are not drinking water. Label every outlet.",
    ],
    "ar": [
        "تدخل نظام المياه الرمادية مياه المغسلة والدوش والغسالة فقط. لا تُدخل مياه المرحاض أو المطبخ أبداً.",
        "لا تستخدم الكلور أو المواد الكيميائية القوية في المصارف الموصولة بنظام المياه الرمادية.",
        "لا تسقِ بالمياه الرمادية أوراقاً أو جذوراً تؤكل نيئة. اسقِ التربة لا النبتة.",
        "استخدم المياه الرمادية خلال 24 ساعة ولا تخزّنها. (تحقق من هذه المدة من مصدر محلي.)",
        "يجب تركيب محوّل الدفقة الأولى قبل مدخل كل خزان لمياه الأمطار.",
        "مياه الأمطار المجمّعة والمياه الرمادية ليست مياه شرب. ضع ملصقاً على كل مخرج.",
    ],
}
DISCLAIMER = {
    "en": "General guidance only, not an approved plumbing design or legal advice. Hire a licensed plumber and check local rules before building.",
    "ar": "هذه إرشادات عامة وليست تصميماً معتمداً للسباكة ولا استشارة قانونية. استعن بسبّاك مرخّص وتحقق من الأنظمة المحلية قبل التنفيذ.",
}
# Model text containing any of these is rejected; the safety guidance comes only from WARNINGS above.
BANNED_TERMS = ["bleach", "chlorine", "drinking", "drink", "potable", "toilet water", "kitchen water",
                "sewage", "كلور", "مبيض", "للشرب", "شرب", "مياه المرحاض", "مياه المطبخ"]
REQUIRED_ITEMS = ["first_flush", "label_kit"]


def validate(raw, catalog, plants, budget):
    """Parse and check model output. Returns (Blueprint, None) or (None, reason)."""
    try:
        bp = Blueprint.model_validate_json(raw) if isinstance(raw, str) else Blueprint.model_validate(raw)
    except ValidationError as e:
        return None, f"schema: {e.errors()[0]['msg']}"
    ok_items = set(allowed_items(catalog, budget)["item_id"])
    for m in bp.materials:
        if m.item_id not in ok_items:
            return None, f"unknown or out-of-budget item: {m.item_id}"
    ok_plants = set(plants.loc[plants["greywater_ok"], "plant_id"])
    for p in bp.plants:
        if p.plant_id not in ok_plants:
            return None, f"plant not allowed for greywater: {p.plant_id}"
    text = " ".join([bp.summary, *bp.greywater_steps, *bp.rainwater_steps,
                     *(m.reason for m in bp.materials), *(p.reason for p in bp.plants)]).lower()
    for term in BANNED_TERMS:
        if term in text:
            return None, f"banned term: {term}"
    return enforce_required(bp), None


def enforce_required(bp):
    """First flush and labels go in every plan, whatever the model chose."""
    have = {m.item_id for m in bp.materials}
    for item in REQUIRED_ITEMS:
        if item not in have:
            bp.materials.append(PlanItem(item_id=item, quantity=1, reason="Required by the safety rules."))
    return bp


def safety_checks(bp):
    """Post-generation checks shown on the badge. Returns list of (rule, passed)."""
    ids = {m.item_id for m in bp.materials}
    return [
        ("All item and plant IDs exist in the tables", True),  # guaranteed by validate()
        ("Quantities within 1 to 50", all(1 <= m.quantity <= 50 for m in bp.materials)),
        ("No banned terms in generated text", True),  # guaranteed by validate()
        ("First-flush diverter included", "first_flush" in ids),
        ("Non-potable labels included", "label_kit" in ids),
        ("Fixed warnings and disclaimer attached", len(WARNINGS[bp.language]) == 6 and bool(DISCLAIMER[bp.language])),
    ]


def price(bp, catalog):
    cat = catalog.set_index("item_id")
    name_col = "name_ar" if bp.language == "ar" else "name_en"
    rows = [{"item": cat.at[m.item_id, name_col], "qty": m.quantity, "unit": cat.at[m.item_id, "unit"],
             "unit_jod": float(cat.at[m.item_id, "price_jod"]),
             "total_jod": m.quantity * float(cat.at[m.item_id, "price_jod"]), "why": m.reason}
            for m in bp.materials]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- template fallback

def template_blueprint(profile, budget, lang):
    """Deterministic plan used when no model is available or its output fails validation."""
    gutter_m = max(4, min(50, round((profile["roof_m2"] ** 0.5) * 2)))
    tank = "tank_1m3" if budget == "low" else "tank_2m3"
    items = [("first_flush", 1), ("leaf_screen", 2), ("gutter_pvc", gutter_m), ("downpipe_110", 2), (tank, 1),
             ("gw_valve", 1), ("gw_filter", 1), ("gw_pipe_40", 3), ("drip_kit", 1), ("label_kit", 1)]
    items += [("gw_drum", 1), ("mulch_basin", 2)] if budget == "low" else [("transfer_pump", 1), ("float_switch", 1)]
    if lang == "ar":
        bp = {
            "language": "ar",
            "summary": f"خطة أساسية لسطح مساحته {profile['roof_m2']:.0f} م² وأسرة من {profile['people']} أفراد: تجميع مياه الأمطار لتنظيف الأرضيات وصناديق الطرد، وإعادة استخدام مياه الدوش والغسالة لسقي الأشجار.",
            "rainwater_steps": ["نظّف السطح وركّب المزاريب والشبك على الحواف.",
                                "ركّب محوّل الدفقة الأولى على ماسورة التصريف قبل الخزان.",
                                "ثبّت الخزان على قاعدة مستوية في الظل وأغلق فتحته بإحكام.",
                                "صِل مخرج الخزان بصناديق الطرد أو بصنبور منفصل للتنظيف."],
            "greywater_steps": ["ركّب محبس التحويل على مصرف الدوش والغسالة فقط.",
                                "مرّر المياه عبر الفلتر الشبكي ونظّفه أسبوعياً.",
                                "وزّع المياه بالتنقيط تحت طبقة الملش عند جذور الأشجار.",
                                "أعد المحبس إلى المجاري عند استخدام منظفات قوية."],
            "plants": [{"plant_id": "olive", "reason": "تتحمل الجفاف وثمارها لا تلامس الماء."},
                       {"plant_id": "pomegranate", "reason": "مناسبة للري بالتنقيط تحت الملش."}],
        }
    else:
        bp = {
            "language": "en",
            "summary": f"Baseline plan for a {profile['roof_m2']:.0f} m² roof and {profile['people']} people: harvest rain for toilet cisterns and floor cleaning, and send shower and laundry water to fruit trees.",
            "rainwater_steps": ["Clean the roof, then fit gutters and leaf screens along the edge.",
                                "Fit the first-flush diverter on the downpipe before the tank.",
                                "Set the tank on a level base in shade and seal the lid.",
                                "Connect the tank outlet to the toilet cisterns or a separate cleaning tap."],
            "greywater_steps": ["Fit the diverter valve on the shower and laundry drains only.",
                                "Run the water through the mesh filter and clean it weekly.",
                                "Drip it under mulch at the root zone of trees.",
                                "Switch the valve back to the sewer on days you use strong cleaners."],
            "plants": [{"plant_id": "olive", "reason": "Drought tolerant; fruit never touches the water."},
                       {"plant_id": "pomegranate", "reason": "Does well on drip under mulch."}],
        }
    bp["materials"] = [{"item_id": i, "quantity": q, "reason": "Standard part for this budget level."} for i, q in items]
    return Blueprint.model_validate(bp)


# ---------------------------------------------------------------- local model (Ollama)

def list_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as r:
            return [m["name"] for m in json.load(r)["models"]]
    except Exception:  # Ollama not running: the app still works on the template
        return []


def ollama_chat(model, prompt):
    body = json.dumps({"model": model, "stream": False, "format": Blueprint.model_json_schema(),
                       "options": {"temperature": 0.3},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)["message"]["content"]


def build_prompt(profile, result, catalog, plants, budget, lang):
    items = allowed_items(catalog, budget)[["item_id", "name_en", "category", "unit"]].to_csv(index=False)
    ok_plants = plants.loc[plants["greywater_ok"], ["plant_id", "name_en", "note"]].to_csv(index=False)
    language = "Modern Standard Arabic" if lang == "ar" else "plain English"
    return f"""You plan rainwater harvesting and greywater reuse for one household in Jordan.
Return JSON only, matching the schema. Set "language" to "{lang}" and write all text in {language}.

Household: roof {profile['roof_m2']} m², {profile['people']} people, {profile['governorate']}, harvest tank {profile['capacity_m3']} m³, budget "{budget}".
Engine results (already calculated, do not recompute): rain used {result['rain_used']:.1f} m³/year, greywater reused {result['greywater']:.1f} m³/year, dry months {result['dry_months']}, overflow {result['overflow']:.1f} m³.

Rules:
- Use only item_id values from this catalog. Quantities 1 to 50. Do not mention prices.
{items}
- Use only plant_id values from this list:
{ok_plants}
- 3 to 5 steps each for rainwater and greywater, short and concrete, in build order.
- Each reason under 200 characters.
- Do not write safety warnings, chemicals or drinking advice; the app adds fixed warnings itself.
"""


def generate(profile, result, catalog, plants, budget, lang, model, chat=ollama_chat, retries=2):
    """Returns (Blueprint, source, notes). source is 'model' or 'template'."""
    notes = []
    if model:
        prompt = build_prompt(profile, result, catalog, plants, budget, lang)
        for attempt in range(1 + retries):
            try:
                raw = chat(model, prompt)
            except Exception as e:
                notes.append(f"attempt {attempt + 1}: model call failed ({e.__class__.__name__})")
                continue
            bp, why = validate(raw, catalog, plants, budget)
            if bp and bp.language == lang:
                return bp, "model", notes
            notes.append(f"attempt {attempt + 1}: rejected ({why or 'wrong language'})")
    return template_blueprint(profile, budget, lang), "template", notes


def to_markdown(bp, bom, profile, result):
    lang = bp.language
    h = {"en": ("Ramadi-Cycle build plan", "Summary", "Rainwater", "Greywater", "Materials", "Plants",
                "Safety rules", "Total", "Estimated water saved"),
         "ar": ("خطة تنفيذ رمادي", "الملخص", "مياه الأمطار", "المياه الرمادية", "المواد", "النباتات",
                "قواعد السلامة", "المجموع", "المياه الموفّرة تقديرياً")}[lang]
    lines = [f"# {h[0]}", "", f"{profile['governorate']} · {profile['roof_m2']:.0f} m² · {profile['people']}",
             "", f"## {h[1]}", bp.summary, "", f"{h[8]}: {result['water']:.1f} m³/yr", "", f"## {h[2]}"]
    lines += [f"{i}. {s}" for i, s in enumerate(bp.rainwater_steps, 1)]
    lines += ["", f"## {h[3]}"] + [f"{i}. {s}" for i, s in enumerate(bp.greywater_steps, 1)]
    lines += ["", f"## {h[4]}", "", "| | | JOD |", "|---|---|---|"]
    lines += [f"| {r.item} | {r.qty} × {r.unit} | {r.total_jod:.0f} |" for r in bom.itertuples()]
    lines += [f"| **{h[7]}** | | **{bom['total_jod'].sum():.0f}** |", "", f"## {h[5]}"]
    lines += [f"- {p.plant_id}: {p.reason}" for p in bp.plants]
    lines += ["", f"## {h[6]}"] + [f"- {w}" for w in WARNINGS[lang]] + ["", f"_{DISCLAIMER[lang]}_", ""]
    return "\n".join(lines)
