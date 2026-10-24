"""Ramadi-Cycle core: water-balance engine, catalog, blueprint schema, safety checks, local model.

Code owns every number, price and safety rule. The model only picks catalog IDs and writes text.
"""
import json
import logging
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, NamedTuple

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

DATA = Path(__file__).parent / "data"
OLLAMA_URL = "http://localhost:11434"
log = logging.getLogger("ramadi")
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


COMMUNITY_MAX_HOMES = 1000  # PRD S2
KG_PER_TONNE = 1000


def format_payback(months):
    """Payback as the UI shows it: whole months, or n/a when the system saves nothing."""
    return "n/a" if months is None else f"{months:.0f} months"


def sareef(result, a, after=True):
    """Sareef counter: yearly trips, JOD and kg CO₂ for the water these uses need, bought today vs with the system.

    delta = now - before, so savings are negative; None when the toggle is off.
    """
    need = float(result["balance"]["demand"].sum() + result["greywater"])
    keys = ("trips", "jod", "co2")
    before = impact(need, 0, a)
    now = impact(max(0.0, need - result["water"]), 0, a) if after else before
    return {"before": {k: before[k] for k in keys}, "now": {k: now[k] for k in keys},
            "delta": {k: now[k] - before[k] for k in keys} if after else None}


def community(result, imp, homes):
    """Scale one home's yearly results linearly to 1..COMMUNITY_MAX_HOMES homes. CO₂ in tonnes."""
    if isinstance(homes, bool) or not isinstance(homes, int) or not 1 <= homes <= COMMUNITY_MAX_HOMES:
        raise InputError(f"homes: must be a whole number from 1 to {COMMUNITY_MAX_HOMES}")
    return {"homes": homes, "water": result["water"] * homes, "trips": imp["trips"] * homes,
            "co2_t": imp["co2"] * homes / KG_PER_TONNE}


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
# Matching is on normalised text (see normalise) and by substring, not whole word: Arabic attaches
# prefixes and suffixes (للشرب, يشرب) and English compounds (undrinkable), so a word-boundary match
# would let real mentions through. A false rejection only costs a retry (PRD §6).
BANNED_TERMS = ["bleach", "chlorine", "chemical", "drinking", "drink", "potable", "toilet", "kitchen",
                "dishwasher", "blackwater", "black water", "sewage",
                "كلور", "مبيض", "كيميا", "للشرب", "شرب", "مرحاض", "مراحيض", "تواليت", "مطبخ", "مجلى",
                "جلاية", "مياه سوداء", "مياه السوداء", "مياه الصرف الصحي"]
# Phrases removed before matching so a rain tank may still feed toilet cisterns (PRD §8).
ALLOWED_PHRASES = ["toilet cistern", "toilet tank", "toilet flushing", "flushing toilet", "flush toilet",
                   "flush the toilet", "طرد المرحاض", "طرد المراحيض"]
REQUIRED_ITEMS = ["first_flush", "label_kit"]
REQUIRED_REASON = {"en": "Required by the safety rules.", "ar": "مطلوب حسب قواعد السلامة."}

# Rejection codes, one per rule, so logs and tests can tell them apart.
EMPTY_RESPONSE = "empty_response"
NOT_JSON = "not_json"
SCHEMA = "schema"
BAD_QUANTITY = "bad_quantity"
WRONG_LANGUAGE = "wrong_language"
UNKNOWN_ITEM = "unknown_item"
ITEM_OVER_BUDGET = "item_over_budget"
BOM_OVER_BUDGET = "bom_over_budget"
UNKNOWN_PLANT = "unknown_plant"
PLANT_NOT_GREYWATER_SAFE = "plant_not_greywater_safe"
BANNED_TERM = "banned_term"


class Rejection(NamedTuple):
    code: str
    detail: str = ""

    def __str__(self):
        return f"{self.code}: {self.detail}" if self.detail else self.code


_FOLD = str.maketrans({"ٱ": "ا", "ة": "ه", "ى": "ي", "\u0640": None})  # wasla, ta marbuta, alef maksura, tatweel


def normalise(text):
    """Lower-case, strip diacritics, tashkeel, tatweel and invisible characters, unify alef/ta/ya forms,
    and turn punctuation and line breaks into single spaces."""
    text = unicodedata.normalize("NFKD", text)  # أ إ آ ؤ ئ split into base letter + mark
    text = "".join(ch for ch in text if unicodedata.category(ch) not in ("Mn", "Me", "Cf"))
    text = unicodedata.normalize("NFKC", text).casefold().translate(_FOLD)
    return " ".join(re.sub(r"[\W_]+", " ", text).split())


def find_banned(text):
    """First banned term in text, or None."""
    t = f" {normalise(text)} "
    for phrase in ALLOWED_PHRASES:
        t = t.replace(normalise(phrase), " ")
    return next((term for term in BANNED_TERMS if normalise(term) in t), None)


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```$", re.DOTALL)


def clean_model_text(raw):
    """Drop <think>…</think> blocks (qwen3, deepseek) and one surrounding code fence."""
    text = _THINK.sub("", raw).strip()
    m = _FENCE.match(text)
    return m.group(1).strip() if m else text


def budget_cap(a, budget):
    """Optional JOD cap on the whole bill of materials, from assumptions.csv row budget_cap_<budget>_jod."""
    return a.get(f"budget_cap_{budget}_jod")


def validate(raw, catalog, plants, budget, lang=None, max_total_jod=None):
    """Parse and check model output. Returns (Blueprint, None) or (None, Rejection)."""
    if isinstance(raw, (str, bytes)):
        text = clean_model_text(raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw)
        if not text:
            return None, Rejection(EMPTY_RESPONSE)
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as e:
            return None, Rejection(NOT_JSON, e.msg)
    try:
        bp = Blueprint.model_validate(raw)
    except ValidationError as e:
        errs = e.errors()
        q = next((err for err in errs if "quantity" in err["loc"]), None)
        if q:
            return None, Rejection(BAD_QUANTITY, q["msg"])
        return None, Rejection(SCHEMA, f"{'.'.join(map(str, errs[0]['loc']))}: {errs[0]['msg']}")
    if lang and bp.language != lang:
        return None, Rejection(WRONG_LANGUAGE, bp.language)
    known_items = set(catalog["item_id"])
    ok_items = set(allowed_items(catalog, budget)["item_id"])
    for m in bp.materials:
        if m.item_id not in known_items:
            return None, Rejection(UNKNOWN_ITEM, m.item_id)
        if m.item_id not in ok_items:
            return None, Rejection(ITEM_OVER_BUDGET, m.item_id)
    known_plants = set(plants["plant_id"])
    ok_plants = set(plants.loc[plants["greywater_ok"], "plant_id"])
    for p in bp.plants:
        if p.plant_id not in known_plants:
            return None, Rejection(UNKNOWN_PLANT, p.plant_id)
        if p.plant_id not in ok_plants:
            return None, Rejection(PLANT_NOT_GREYWATER_SAFE, p.plant_id)
    text = " \n ".join([bp.summary, *bp.greywater_steps, *bp.rainwater_steps,
                        *(m.reason for m in bp.materials), *(p.reason for p in bp.plants)])
    if term := find_banned(text):
        return None, Rejection(BANNED_TERM, term)
    bp = enforce_required(bp)
    if max_total_jod is not None and (total := plan_cost(price(bp, catalog))) > max_total_jod:
        return None, Rejection(BOM_OVER_BUDGET, f"{total:.0f} > {max_total_jod:.0f} JOD")
    return bp, None


def enforce_required(bp):
    """First flush and labels go in every plan, whatever the model chose."""
    have = {m.item_id for m in bp.materials}
    for item in REQUIRED_ITEMS:
        if item not in have:
            bp.materials.append(PlanItem(item_id=item, quantity=1, reason=REQUIRED_REASON[bp.language]))
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


BOM_COLUMNS = ["item", "qty", "unit", "unit_jod", "total_jod", "why"]


def price(bp, catalog):
    """Bill of materials priced from catalog.csv, in the plan's language."""
    cat = catalog.set_index("item_id")
    name_col = "name_ar" if bp.language == "ar" else "name_en"
    rows = [{"item": cat.at[m.item_id, name_col], "qty": m.quantity, "unit": cat.at[m.item_id, "unit"],
             "unit_jod": float(cat.at[m.item_id, "price_jod"]),
             "total_jod": m.quantity * float(cat.at[m.item_id, "price_jod"]), "why": m.reason}
            for m in bp.materials]
    return pd.DataFrame(rows, columns=BOM_COLUMNS)


def plan_cost(bom):
    """Total JOD of a priced bill of materials."""
    return float(bom["total_jod"].sum())


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

# One first call plus two retries (PRD M7 "two retries"). PRD §4 says "fails twice"; see AUDIT.md.
MAX_ATTEMPTS = 3
LIST_TIMEOUT_S = 2
CHAT_TIMEOUT_S = 180
# Fixed sampling so the same inputs give the same plan on the demo laptop.
MODEL_OPTIONS = {"temperature": 0.3, "seed": 42}


class ModelError(Exception):
    """The local model could not be reached or answered with something other than a chat reply."""
    code = "model_error"
    retry = False  # True when another attempt may succeed


class ModelUnavailable(ModelError):
    code = "unavailable"  # Ollama not running, connection refused or reset


class ModelTimeout(ModelError):
    code = "timeout"


class ModelNotFound(ModelError):
    code = "model_not_pulled"


class BadResponse(ModelError):
    code = "bad_response"  # HTTP 5xx or a reply without message.content
    retry = True


def list_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=LIST_TIMEOUT_S) as resp:
            return [m["name"] for m in json.load(resp)["models"]]
    except Exception:  # Ollama not running or not installed: the app still works on the template
        return []


def ollama_chat(model, prompt):
    """One non-streaming chat call. Returns the reply text or raises a ModelError subclass."""
    body = json.dumps({"model": model, "stream": False, "format": Blueprint.model_json_schema(),
                       "options": MODEL_OPTIONS,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT_S) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ModelNotFound(f"{model} is not pulled") from None
        raise BadResponse(f"HTTP {e.code}") from None
    except TimeoutError:
        raise ModelTimeout(f"no reply within {CHAT_TIMEOUT_S} s") from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise ModelTimeout(f"no reply within {CHAT_TIMEOUT_S} s") from None
        raise ModelUnavailable(str(e.reason)) from None
    except (ValueError, UnicodeDecodeError):
        raise BadResponse("reply is not JSON") from None
    except OSError as e:
        raise ModelUnavailable(e.__class__.__name__) from None
    content = (payload.get("message") or {}).get("content") if isinstance(payload, dict) else None
    if not isinstance(content, str):
        raise BadResponse("reply has no message.content")
    return content


def as_model_error(e):
    """Map any exception from a chat function to a ModelError, so callers handle one family."""
    if isinstance(e, ModelError):
        return e
    if isinstance(e, TimeoutError):
        return ModelTimeout(str(e) or "timed out")
    if isinstance(e, (ConnectionError, urllib.error.URLError)):
        return ModelUnavailable(str(e) or e.__class__.__name__)
    return BadResponse(e.__class__.__name__)


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


class Generation(NamedTuple):
    blueprint: "Blueprint"
    source: Literal["model", "template"]
    notes: list  # one line per failed attempt: "attempt N: <code>: <detail>"


def generate(profile, result, catalog, plants, budget, lang, model, chat=None, max_total_jod=None):
    """Ask the model for a plan, validate it, and fall back to the template. Never raises for model failures.

    Output problems (prose, bad JSON, schema, validation) are retried up to MAX_ATTEMPTS calls in all.
    Transport problems (not running, model not pulled, timeout) stop at once: retrying cannot help and
    a timeout already cost CHAT_TIMEOUT_S.
    """
    chat = chat or ollama_chat  # looked up at call time so tests can replace it
    notes = []
    if model:
        prompt = build_prompt(profile, result, catalog, plants, budget, lang)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw = chat(model, prompt)
            except Exception as e:  # noqa: BLE001 - every failure must end in the template
                err = as_model_error(e)
                notes.append(f"attempt {attempt}: {err.code}: {err}")
                log.info("model attempt %d failed: %s", attempt, err.code)
                if err.retry:
                    continue
                break
            bp, why = validate(raw, catalog, plants, budget, lang, max_total_jod)
            if bp:
                return Generation(bp, "model", notes)
            notes.append(f"attempt {attempt}: rejected: {why}")
            log.info("model attempt %d rejected: %s", attempt, why.code)  # code only, no user data
    return Generation(template_blueprint(profile, budget, lang), "template", notes)


def fallback_notice(gen, model):
    """On-screen notice for a template plan, or None for a model plan."""
    if gen.source == "model":
        return None
    if not model:
        return "Showing the built-in template plan. No local model was available (Ollama is not running or has no models)."
    return f"Showing the built-in template plan. {model} could not produce a valid plan: " + "; ".join(gen.notes)


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
    if lang == "ar":  # blank lines keep the Markdown inside the block rendered
        lines = ['<div dir="rtl" lang="ar">', ""] + lines + ["</div>", ""]
    return "\n".join(lines)
