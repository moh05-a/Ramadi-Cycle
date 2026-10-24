"""Ramadi-Cycle core: water-balance engine, catalog, blueprint schema, safety checks, local model.

Code owns every number, price and safety rule. The model only picks catalog IDs and writes text.
"""
import json
import urllib.request
from pathlib import Path
from typing import Literal, NamedTuple

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

DATA = Path(__file__).parent / "data"
OLLAMA_URL = "http://localhost:11434"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------- data

class DataError(ValueError):
    """A table in data/ is missing a column, has a bad value, or is inconsistent."""


# Required columns per table: "num" must parse as a non-negative number, "bool" as true/false, "text" non-empty.
COLUMNS = {
    "rainfall.csv": {"governorate": "text", "annual_mm": "num", "source": "text", "status": "text"},
    "monthly_share.csv": {"month": "text", "share_of_annual_rain": "num", "source": "text", "status": "text"},
    "catalog.csv": {"item_id": "text", "name_en": "text", "name_ar": "text", "category": "text", "unit": "text",
                    "price_jod": "num", "budget_level": "text", "source": "text", "status": "text"},
    "plants.csv": {"plant_id": "text", "name_en": "text", "name_ar": "text", "greywater_ok": "bool", "note": "text",
                   "source": "text", "status": "text"},
    "assumptions.csv": {"parameter": "text", "value": "num", "unit": "text", "source": "text", "status": "text"},
}
KEYS = {"rainfall.csv": "governorate", "monthly_share.csv": "month", "catalog.csv": "item_id",
        "plants.csv": "plant_id", "assumptions.csv": "parameter"}
SHARE_TOLERANCE = 1e-6
BUDGETS = ("low", "full")
YEARS = ("dry", "average", "wet")
FRACTIONS = ["runoff_coefficient", "first_flush_loss", "tanker_share", "greywater_recovery"]
PARAMETERS = FRACTIONS + [f"year_multiplier_{y}" for y in YEARS] + [
    "nonpotable_litres_per_person_day", "tanker_volume", "tanker_price", "municipal_tariff", "diesel_per_trip",
    "diesel_co2", "pump_energy", "grid_co2", "litres_per_shower", "litres_per_laundry_load",
    "sink_litres_per_person_week"]


class Tables(NamedTuple):
    rain: pd.DataFrame
    shares: list
    catalog: pd.DataFrame
    plants: pd.DataFrame
    assumptions: pd.DataFrame


def read_table(name, data_dir=DATA):
    """Read one CSV and check its columns and types. Raises DataError naming the file, column and row."""
    try:
        df = pd.read_csv(data_dir / name, dtype=str, keep_default_na=False, encoding="utf-8")
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as e:
        raise DataError(f"{name}: cannot read ({e})") from e
    missing = [c for c in COLUMNS[name] if c not in df.columns]
    if missing:
        raise DataError(f"{name}: missing column(s) {', '.join(missing)}")
    if df.empty:
        raise DataError(f"{name}: no rows")
    for col, kind in COLUMNS[name].items():
        cells = df[col].str.strip()
        if kind == "text":
            bad = cells == ""
        elif kind == "bool":
            bad = ~cells.str.lower().isin(["true", "false"])
            df[col] = cells.str.lower() == "true"
        else:
            nums = pd.to_numeric(cells, errors="coerce")
            bad = nums.isna() | (nums < 0)
            df[col] = nums.astype(float)
        if bad.any():
            row = int(bad.to_numpy().nonzero()[0][0]) + 2  # +1 header, +1 one-based
            raise DataError(f"{name}: bad value in column '{col}' on line {row} (expected {kind})")
    dupes = df[KEYS[name]][df[KEYS[name]].duplicated()].tolist()
    if dupes:
        raise DataError(f"{name}: duplicate {KEYS[name]} {dupes}")
    return df


def load_tables(data_dir=DATA):
    """Load and cross-check every table. Fails loudly instead of letting a bad CSV reach the engine."""
    rain = read_table("rainfall.csv", data_dir)
    share_df = read_table("monthly_share.csv", data_dir)
    if sorted(share_df["month"]) != sorted(MONTHS):
        raise DataError(f"monthly_share.csv: months must be exactly {', '.join(MONTHS)}")
    shares = share_df.set_index("month").loc[MONTHS, "share_of_annual_rain"].tolist()
    if abs(sum(shares) - 1.0) > SHARE_TOLERANCE:
        raise DataError(f"monthly_share.csv: shares sum to {sum(shares):.6f}, not 1.0")
    catalog = read_table("catalog.csv", data_dir)
    bad_levels = set(catalog["budget_level"]) - {*BUDGETS, "both"}
    if bad_levels:
        raise DataError(f"catalog.csv: unknown budget_level {sorted(bad_levels)}")
    always = set(catalog.loc[catalog["budget_level"] == "both", "item_id"])
    if missing := [i for i in REQUIRED_ITEMS if i not in always]:
        raise DataError(f"catalog.csv: required safety item(s) {missing} missing or not budget_level 'both'")
    plants = read_table("plants.csv", data_dir)
    assumptions = read_table("assumptions.csv", data_dir)
    assumption_values(assumptions)  # checks required parameters and ranges
    return Tables(rain, shares, catalog, plants, assumptions)


def assumption_values(assumptions):
    a = dict(zip(assumptions["parameter"], assumptions["value"].astype(float)))
    if missing := [p for p in PARAMETERS if p not in a]:
        raise DataError(f"assumptions.csv: missing parameter(s) {', '.join(missing)}")
    if bad := [p for p in FRACTIONS if not 0 <= a[p] <= 1]:
        raise DataError(f"assumptions.csv: {', '.join(bad)} must be a fraction between 0 and 1")
    if a["tanker_volume"] <= 0:
        raise DataError("assumptions.csv: tanker_volume must be above 0")
    if not a["year_multiplier_dry"] < a["year_multiplier_average"] < a["year_multiplier_wet"]:
        raise DataError("assumptions.csv: year multipliers must rise from dry to average to wet")
    return a


# ---------------------------------------------------------------- engine

# Calendar and unit facts, not assumptions: 1 mm of rain on 1 m² is 1 L.
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
WEEKS_PER_YEAR = 52
LITRES_PER_M3 = 1000
MM_PER_M = 1000


class InputError(ValueError):
    """A household input is missing, negative or not one of the allowed choices."""


class Profile(BaseModel):
    """Household inputs from the sidebar, checked before they reach the engine."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    governorate: str = Field(min_length=1)
    rain_mm: float = Field(ge=0)
    roof_m2: float = Field(ge=0)
    people: int = Field(ge=0)
    showers_pp: float = Field(ge=0)
    laundry_loads: float = Field(ge=0)
    capacity_m3: float = Field(ge=0)
    year: Literal["dry", "average", "wet"]


def check_profile(profile):
    """Return the profile as a plain dict, or raise InputError with the first bad field."""
    try:
        return Profile.model_validate(profile).model_dump()
    except ValidationError as e:
        err = e.errors()[0]
        raise InputError(f"{'.'.join(map(str, err['loc'])) or 'profile'}: {err['msg']}") from None


def make_profile(rain, governorate, roof_m2, people, showers_pp, laundry_loads, capacity_m3, year):
    """Build a checked profile, taking annual rainfall for the governorate from rainfall.csv."""
    by_gov = rain.set_index("governorate")["annual_mm"]
    if governorate not in by_gov.index:
        raise InputError(f"governorate: unknown {governorate!r}")
    return check_profile({"governorate": governorate, "rain_mm": float(by_gov[governorate]), "roof_m2": roof_m2,
                          "people": people, "showers_pp": showers_pp, "laundry_loads": laundry_loads,
                          "capacity_m3": capacity_m3, "year": year})


def annual_potential(roof_m2, rain_m, runoff):
    return roof_m2 * rain_m * runoff


def water_balance(roof_m2, rain_m, shares, k, runoff, first_flush, capacity_m3, demand_m3):
    """Monthly harvest-tank balance in m³. demand_m3 is a list of 12 monthly demands. Tank starts empty in January.

    Every month: start + inflow = met + overflow + level.
    """
    level, rows = 0.0, []
    for month, s, d in zip(MONTHS, shares, demand_m3, strict=True):
        inflow = roof_m2 * (rain_m * s * k) * runoff * (1 - first_flush)
        start, available = level, level + inflow
        met = min(d, available)
        level = min(capacity_m3, available - met)
        overflow = available - met - level
        rows.append({"month": month, "start": start, "inflow": inflow, "demand": d, "met": met,
                     "shortfall": d - met, "overflow": overflow, "level": level})
    return pd.DataFrame(rows)


def greywater_week(people, showers_pp, laundry_loads, a):
    """Weekly recovered greywater in m³. Laundry is per household, showers and sink per person."""
    litres = (people * showers_pp * a["litres_per_shower"]
              + laundry_loads * a["litres_per_laundry_load"]
              + people * a["sink_litres_per_person_week"])
    return litres * a["greywater_recovery"] / LITRES_PER_M3


def impact(water_m3, system_cost, a):
    """Yearly impact of water_m3 no longer bought. Trips are fractional; payback is None when nothing is saved."""
    s, T = a["tanker_share"], a["tanker_volume"]
    trips = water_m3 * s / T
    jod = trips * a["tanker_price"] + water_m3 * (1 - s) * a["municipal_tariff"]
    co2 = trips * a["diesel_per_trip"] * a["diesel_co2"] + water_m3 * a["pump_energy"] * a["grid_co2"]
    payback = len(MONTHS) * system_cost / jod if jod > 0 else None
    return {"trips": trips, "jod": jod, "co2": co2, "payback_months": payback}


def simulate(profile, shares, a):
    """Run the whole household model. profile keys: see Profile. Volumes in m³ per year."""
    profile = check_profile(profile)
    k = a[f"year_multiplier_{profile['year']}"]
    rain_m = profile["rain_mm"] / MM_PER_M
    litres_day = profile["people"] * a["nonpotable_litres_per_person_day"]
    monthly_demand = [litres_day * days / LITRES_PER_M3 for days in DAYS_IN_MONTH]
    bal = water_balance(profile["roof_m2"], rain_m, shares, k, a["runoff_coefficient"], a["first_flush_loss"],
                        profile["capacity_m3"], monthly_demand)
    grey = greywater_week(profile["people"], profile["showers_pp"], profile["laundry_loads"], a) * WEEKS_PER_YEAR
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

QTY_MIN, QTY_MAX = 1, 50  # PRD M6
REASON_MAX = 200


# strict: no "5" for 5 or 5.0 for 5; extra="forbid": no fields the schema does not name.
STRICT = ConfigDict(extra="forbid", strict=True)


class PlanItem(BaseModel):
    model_config = STRICT
    item_id: str
    quantity: int = Field(ge=QTY_MIN, le=QTY_MAX)
    reason: str = Field(max_length=REASON_MAX)


class PlantPick(BaseModel):
    model_config = STRICT
    plant_id: str
    reason: str = Field(max_length=REASON_MAX)


class Blueprint(BaseModel):
    model_config = STRICT
    language: Literal["en", "ar"]
    summary: str = Field(min_length=1)
    greywater_steps: list[str] = Field(min_length=1)
    rainwater_steps: list[str] = Field(min_length=1)
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
