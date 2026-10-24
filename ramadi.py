"""Ramadi-Cycle core: water-balance engine, catalog, blueprint schema, safety checks, local model.

Code owns every number, price and safety rule. The model only picks catalog IDs and writes text.
"""
import json
import logging
import os
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
    "et0.csv": {"governorate": "text", **{m: "num" for m in MONTHS}, "source": "text", "status": "text"},
    "garden_plants.csv": {"plant_id": "text", "kind": "text", "kc_ini": "num", "kc_mid": "num", "kc_end": "num",
                          "deciduous": "bool", "canopy_m2": "num", "salt": "text", "source": "text", "status": "text"},
    "humidity.csv": {"governorate": "text", **{m: "num" for m in MONTHS}, "source": "text", "status": "text"},
    "soil.csv": {"governorate": "text", "sand_pct": "num", "silt_pct": "num", "clay_pct": "num", "ph": "num",
                 "texture": "text", "km_from_point": "num", "source": "text", "status": "text"},
}
KEYS = {"rainfall.csv": "governorate", "monthly_share.csv": "month", "catalog.csv": "item_id",
        "plants.csv": "plant_id", "assumptions.csv": "parameter", "et0.csv": "governorate",
        "garden_plants.csv": "plant_id", "humidity.csv": "governorate", "soil.csv": "governorate"}
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
STEPS_MIN, STEPS_MAX = 3, 5  # per list, as the prompt asks


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
    greywater_steps: list[str] = Field(min_length=STEPS_MIN, max_length=STEPS_MAX)
    rainwater_steps: list[str] = Field(min_length=STEPS_MIN, max_length=STEPS_MAX)
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
BANNED_TERMS = ["bleach", "chlorine", "chlorin", "clorox", "chemical", "drinking", "drink", "potable", "toilet",
                "kitchen", "dishwasher", "blackwater", "black water", "sewage",
                "consume", "cook", "lavator", "wc", "washing up",
                "كلور", "مبيض", "كيميا", "للشرب", "شرب", "مرحاض", "مراحيض", "تواليت", "مطبخ", "مجلى",
                "جلاية", "مياه سوداء", "مياه السوداء", "مياه الصرف الصحي", "طبخ", "طهي"]
# Phrases removed before matching so a rain tank may still feed toilet cisterns (PRD §8).
ALLOWED_PHRASES = ["toilet cistern", "toilet tank", "toilet flushing", "flushing toilet", "flush toilet",
                   "flush the toilet", "طرد المرحاض", "طرد المراحيض"]
REQUIRED_ITEMS = ["first_flush", "label_kit"]
REQUIRED_REASON = {"en": "Required by the safety rules.", "ar": "مطلوب حسب قواعد السلامة."}
SIZED_REASON = {"en": "Sized by code to run along the whole roof edge.", "ar": "حدّد الكود طوله ليغطي حافة السطح كاملة."}

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
WRONG_SCRIPT = "wrong_script"
SCRIPT_MAX_FOREIGN = 0.3  # share of letters from the other script above which a plan is rejected


ID_SHOWN_MAX = 40
_UNSAFE_ID = re.compile(r"[^A-Za-z0-9_.:-]")


def shown_id(value):
    """A model-chosen ID as it may appear in a notice or a retry prompt: safe characters only, length capped,
    so a made-up ID can't carry Markdown, links or a long injected instruction onto the screen or back in."""
    return _UNSAFE_ID.sub("?", str(value))[:ID_SHOWN_MAX]


class Rejection(NamedTuple):
    code: str
    detail: str = ""

    def __str__(self):
        return f"{self.code}: {self.detail}" if self.detail else self.code


_FOLD = str.maketrans({"ٱ": "ا", "ة": "ه", "ى": "ي", "\u0640": None,  # wasla, ta marbuta, alef maksura, tatweel
                       # Cyrillic letters that look Latin, so "pоtable" with a Cyrillic о is still caught
                       "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s"})


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


def parse_reply(raw):
    """Model reply text to a Python object. Returns (obj, None) or (None, Rejection). Non-text passes through."""
    if not isinstance(raw, (str, bytes)):
        return raw, None
    text = clean_model_text(raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw)
    if not text:
        return None, Rejection(EMPTY_RESPONSE)
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, Rejection(NOT_JSON, e.msg)


def validate(raw, catalog, plants, budget, lang=None, max_total_jod=None, profile=None):
    """Parse and check model output. Returns (Blueprint, None) or (None, Rejection)."""
    raw, why = parse_reply(raw)
    if why:
        return None, why
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
            return None, Rejection(UNKNOWN_ITEM, shown_id(m.item_id))
        if m.item_id not in ok_items:
            return None, Rejection(ITEM_OVER_BUDGET, shown_id(m.item_id))
    known_plants = set(plants["plant_id"])
    ok_plants = set(plants.loc[plants["greywater_ok"], "plant_id"])
    for p in bp.plants:
        if p.plant_id not in known_plants:
            return None, Rejection(UNKNOWN_PLANT, shown_id(p.plant_id))
        if p.plant_id not in ok_plants:
            return None, Rejection(PLANT_NOT_GREYWATER_SAFE, shown_id(p.plant_id))
    text = " \n ".join([bp.summary, *bp.greywater_steps, *bp.rainwater_steps,
                        *(m.reason for m in bp.materials), *(p.reason for p in bp.plants)])
    if term := find_banned(text):
        return None, Rejection(BANNED_TERM, term)
    if (share := foreign_share(text, bp.language)) > SCRIPT_MAX_FOREIGN:
        return None, Rejection(WRONG_SCRIPT, f"{share:.0%} of letters are not {bp.language}")
    bp = enforce_required(bp, profile, budget)
    if max_total_jod is not None and (total := plan_cost(price(bp, catalog))) > max_total_jod:
        return None, Rejection(BOM_OVER_BUDGET, f"{total:.0f} > {max_total_jod:.0f} JOD")
    return bp, None


def foreign_share(text, lang):
    """Share of letters in text from the other script: Latin in an Arabic plan, Arabic in an English one."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    latin = sum("a" <= c.lower() <= "z" for c in letters)
    return (latin if lang == "ar" else len(letters) - latin) / len(letters)


def gutter_metres(roof_m2):
    """Gutter needed for a square roof's perimeter, roughly: 2 × √area metres, kept within catalogue limits."""
    return max(4, min(QTY_MAX, round((roof_m2 ** 0.5) * 2)))


def tank_for(budget):
    return "tank_1m3" if budget == "low" else "tank_2m3"


def enforce_required(bp, profile=None, budget=None):
    """Code-owned minimums, whatever the model chose: first flush and labels always; with a profile, also a tank
    and enough gutter for the roof, so a model can't make the system look cheaper by leaving parts out."""
    have = {m.item_id: m for m in bp.materials}
    for item in REQUIRED_ITEMS:
        if item not in have:
            bp.materials.append(PlanItem(item_id=item, quantity=1, reason=REQUIRED_REASON[bp.language]))
    if profile is None or budget is None:
        return bp
    if not any(i.startswith("tank_") for i in have):
        bp.materials.append(PlanItem(item_id=tank_for(budget), quantity=1, reason=REQUIRED_REASON[bp.language]))
    need = gutter_metres(profile["roof_m2"])
    if "gutter_pvc" not in have:
        bp.materials.append(PlanItem(item_id="gutter_pvc", quantity=need, reason=SIZED_REASON[bp.language]))
    elif have["gutter_pvc"].quantity < need:
        have["gutter_pvc"].quantity = need
        have["gutter_pvc"].reason = SIZED_REASON[bp.language]
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
    gutter_m = gutter_metres(profile["roof_m2"])
    tank = tank_for(budget)
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
            "plants": [],  # plant suggestions only come from a model (the garden planner)
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
            "plants": [],  # plant suggestions only come from a model (the garden planner)
        }
    reason = "قطعة أساسية لهذه الميزانية." if lang == "ar" else "Standard part for this budget level."
    bp["materials"] = [{"item_id": i, "quantity": q, "reason": reason} for i, q in items]
    return Blueprint.model_validate(bp)


def system_cost(profile, budget, catalog):
    """JOD used for payback: the standard (template) parts list for this budget. It never depends on what a model
    picked, so payback stays a code-owned number (PRD §6); the plan's own parts total is shown separately."""
    return plan_cost(price(template_blueprint(profile, budget, "en"), catalog))


# ---------------------------------------------------------------- local model (Ollama)

# One first call plus two retries (PRD M7 "two retries"). PRD §4 says "fails twice"; see AUDIT.md.
MAX_ATTEMPTS = 3
LIST_TIMEOUT_S = 2
CHAT_TIMEOUT_S = 180
# Fixed sampling so the same inputs give the same plan on the demo laptop.
MODEL_OPTIONS = {"temperature": 0.3, "seed": 42}
# Keep the model in memory between requests, so the garden after a build plan doesn't pay to reload it.
KEEP_ALIVE = "30m"


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
    """Installed Ollama models, then OpenRouter models if OPENROUTER_API_KEY is set."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=LIST_TIMEOUT_S) as resp:
            local = [m["name"] for m in json.load(resp)["models"]]
    except Exception:  # Ollama not running or not installed: the app still works on the template
        local = []
    return local + openrouter_models()


def ollama_chat(model, prompt, schema=None):
    """One non-streaming chat call constrained to schema (default: Blueprint). Returns the reply text or raises
    a ModelError subclass."""
    body = json.dumps({"model": model, "stream": False, "format": schema or Blueprint.model_json_schema(),
                       "options": MODEL_OPTIONS, "keep_alive": KEEP_ALIVE,
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


# ---------------------------------------------------------------- optional cloud models (OpenRouter)

# Off unless OPENROUTER_API_KEY is set. A cloud model sends the household numbers and prompt to OpenRouter,
# so the UI labels it; the local Ollama path stays the default and the app still runs offline without it.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_PREFIX = "openrouter:"
# Open-weight models only, to stay within the open-source AI challenge. Override with OPENROUTER_MODELS=a,b,c.
# The ":free" ones work on a free-tier key (no credit, about 50 requests a day) but are often busy upstream.
OPENROUTER_MODELS = ["liquid/lfm-2.5-2.6b:free", "google/gemma-4-26b-a4b-it:free", "google/gemma-4-31b-it:free",
                     "qwen/qwen3.6-35b-a3b", "mistralai/mistral-small-3.2-24b-instruct",
                     "meta-llama/llama-3.3-70b-instruct"]
OPENROUTER_ERROR_MAX = 160  # characters of OpenRouter's error message kept in the on-screen notes


def _openrouter_reason(e):
    """OpenRouter's own error message from an HTTPError body, e.g. 'Key limit exceeded', or '' if none."""
    try:
        err = json.loads(e.read() or b"{}").get("error") or {}
        text = (err.get("metadata") or {}).get("raw") or err.get("message") or ""
    except (ValueError, AttributeError, OSError):
        return ""
    return f": {str(text)[:OPENROUTER_ERROR_MAX]}" if text else ""


def is_cloud(model):
    return bool(model) and model.startswith(OPENROUTER_PREFIX)


def openrouter_models():
    if not os.environ.get("OPENROUTER_API_KEY"):
        return []
    custom = os.environ.get("OPENROUTER_MODELS")
    ids = [m.strip() for m in custom.split(",") if m.strip()] if custom else OPENROUTER_MODELS
    return [OPENROUTER_PREFIX + m for m in ids]


def openrouter_chat(model, prompt, schema=None):
    """One chat call to OpenRouter constrained to schema (default: Blueprint). Returns the reply text or raises
    a ModelError subclass."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ModelUnavailable("OPENROUTER_API_KEY is not set")
    schema = schema or Blueprint.model_json_schema()
    body = json.dumps({
        "model": model.removeprefix(OPENROUTER_PREFIX),
        **MODEL_OPTIONS,
        "messages": [{"role": "system", "content": "Reply with one JSON object matching this JSON schema:\n" + json.dumps(schema)},
                     {"role": "user", "content": prompt}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": schema.get("title", "blueprint").lower(), "strict": True, "schema": schema}},
    }).encode()
    req = urllib.request.Request(OPENROUTER_URL, body, {
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
        "X-Title": "Ramadi-Cycle", "HTTP-Referer": "https://github.com/moh05-a/Ramadi-Cycle"})
    try:
        with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT_S) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        why = _openrouter_reason(e)
        if e.code == 404:
            raise ModelNotFound(f"{model} is not on OpenRouter{why}") from None
        if e.code == 429 or e.code >= 500:
            raise BadResponse(f"HTTP {e.code}{why}") from None  # rate limit or provider error: a retry may work
        raise ModelUnavailable(f"OpenRouter refused the request (HTTP {e.code}){why}") from None  # bad key, no credit
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
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise BadResponse("reply has no choices[0].message.content") from None
    if not isinstance(content, str):
        raise BadResponse("reply has no choices[0].message.content")
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
    """Fixed text first and the household last, so Ollama reuses the cached prefix between households.

    On a CPU the reply costs far more than the prompt, so the length limits matter most.
    """
    items = "\n".join(f"{i}: {n}" for i, n in allowed_items(catalog, budget)[["item_id", "name_en"]].values)
    ok_plants = ", ".join(plants.loc[plants["greywater_ok"], "plant_id"])
    language = "Modern Standard Arabic" if lang == "ar" else "plain English"
    required = ", ".join(REQUIRED_ITEMS)
    return f"""Plan rainwater harvesting and greywater reuse for a household in Jordan. Reply with compact JSON on one line, matching the schema. Set "language" to "{lang}" and write all text in {language}.

Keep it short:
- summary: one sentence.
- rainwater_steps and greywater_steps: exactly 3 each, in build order, under 15 words each.
- materials: 3 to 6 items, item_id only from the list below, quantity 1 to 50. {required} are added for you.
- plants: 1 or 2, plant_id only from: {ok_plants}.
- every reason: under 10 words.
- Only say what to build and where. Do not discuss prices, water quality or safety; the app adds those.

Items ({budget} budget):
{items}

Household: {profile['governorate']}, roof {profile['roof_m2']:g} m², {profile['people']} people, tank {profile['capacity_m3']:g} m³. Rain used {result['rain_used']:.1f} m³/yr, greywater {result['greywater']:.1f} m³/yr, {result['dry_months']} dry months, overflow {result['overflow']:.1f} m³.
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
    chat = chat or (openrouter_chat if is_cloud(model) else ollama_chat)  # looked up at call time so tests can replace it
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
            bp, why = validate(raw, catalog, plants, budget, lang, max_total_jod, profile)
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
    lines += [f"| **{h[7]}** | | **{bom['total_jod'].sum():.0f}** |"]
    if bp.plants:
        lines += ["", f"## {h[5]}"] + [f"- {p.plant_id}: {p.reason}" for p in bp.plants]
    lines += ["", f"## {h[6]}"] + [f"- {w}" for w in WARNINGS[lang]] + ["", f"_{DISCLAIMER[lang]}_", ""]
    if lang == "ar":  # blank lines keep the Markdown inside the block rendered
        lines = ['<div dir="rtl" lang="ar">', ""] + lines + ["</div>", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- garden planner

# The model designs the garden; code works out every litre. Garden water is greywater (every day) plus rain-tank
# overflow (winter). A mature plant needs (ET0 × Kc − effective rain) × canopy ÷ drip efficiency each month, and a
# plan passes only if that fits the water in every month and the plants fit the garden.
GARDEN_COUNT_MAX = 20
GARDEN_M2_MAX = 1000
GARDEN_STEPS = 3
GARDEN_KINDS_MAX = 6
WISHES_MAX = 300
SALT_SENSITIVE = {"sensitive", "moderately sensitive"}
GARDEN_WARNINGS = [0, 1, 2, 3]  # the greywater rules from WARNINGS

GARDEN_SHORT = "garden_short"
GARDEN_TOO_BIG = "garden_too_big"
EMPTY_GARDEN = "empty_garden"
DUPLICATE_PLANT = "duplicate_plant"


class Garden(NamedTuple):
    et0: pd.DataFrame       # et0.csv indexed by governorate: mm per month
    plants: pd.DataFrame    # garden_plants.csv indexed by plant_id, with name_en and name_ar from plants.csv
    humidity: pd.DataFrame  # humidity.csv indexed by governorate: % per month
    soil: pd.DataFrame      # soil.csv indexed by governorate


def load_garden(rain, plants, data_dir=DATA):
    """Load and cross-check the garden tables against rainfall.csv and plants.csv."""
    by_gov = {}
    for name in ("et0.csv", "humidity.csv", "soil.csv"):
        by_gov[name] = read_table(name, data_dir).set_index("governorate")
        if missing := sorted(set(rain["governorate"]) - set(by_gov[name].index)):
            raise DataError(f"{name}: no row for {', '.join(missing)}")
    gp = read_table("garden_plants.csv", data_dir).set_index("plant_id")
    names = plants.set_index("plant_id")
    if unknown := sorted(set(gp.index) - set(names.index)):
        raise DataError(f"garden_plants.csv: {', '.join(unknown)} not in plants.csv")
    if unsafe := sorted(p for p in gp.index if not names.at[p, "greywater_ok"]):
        raise DataError(f"garden_plants.csv: {', '.join(unsafe)} not greywater-safe in plants.csv")
    return Garden(by_gov["et0.csv"], gp.join(names[["name_en", "name_ar"]]), by_gov["humidity.csv"], by_gov["soil.csv"])


def kc_by_month(row):
    """Simplified FAO-56 crop curve: kc_ini in Mar-Apr, kc_mid in May-Aug, kc_end in Sep-Oct. Over winter
    evergreens stay at kc_ini and deciduous plants are bare (0) from December to February."""
    winter = 0.0 if row["deciduous"] else row["kc_ini"]
    nov = row["kc_end"] if row["deciduous"] else row["kc_ini"]
    return [winter, winter, row["kc_ini"], row["kc_ini"], *[row["kc_mid"]] * 4, row["kc_end"], row["kc_end"], nov, winter]


def effective_rain(p_mm):
    """Share of a month's rain plants can use, in mm: FAO/AGLW dependable-rain formula (Smith 1992, CROPWAT)."""
    return max(0.0, 0.6 * p_mm - 10) if p_mm <= 70 else 0.8 * p_mm - 24


def plant_need(row, et0, rain_mm, drip):
    """Litres one mature plant needs from the drip line each month. 1 mm on 1 m² is 1 L."""
    return [max(0.0, e * kc - effective_rain(p)) * row["canopy_m2"] / drip
            for e, kc, p in zip(et0, kc_by_month(row), rain_mm, strict=True)]


def per_week(litres, month):
    """A month's litres as litres per week."""
    return litres / DAYS_IN_MONTH[month] * 7


def garden_context(profile, result, shares, a, garden, garden_m2):
    """Everything code knows about one garden: litres available and litres each plant needs, per month."""
    if isinstance(garden_m2, bool) or not 0 < garden_m2 <= GARDEN_M2_MAX:
        raise InputError(f"garden_m2: must be above 0 and at most {GARDEN_M2_MAX}")
    drip = a.get("drip_efficiency")
    if drip is None or not 0 < drip <= 1:
        raise DataError("assumptions.csv: drip_efficiency must be a fraction above 0")
    k = a[f"year_multiplier_{profile['year']}"]
    rain_mm = [profile["rain_mm"] * s * k for s in shares]
    et0 = garden.et0.loc[profile["governorate"], MONTHS].astype(float).tolist()
    grey_day = result["greywater"] / WEEKS_PER_YEAR / 7 * LITRES_PER_M3
    supply = [grey_day * d + o * LITRES_PER_M3 for d, o in zip(DAYS_IN_MONTH, result["balance"]["overflow"])]
    need = {pid: plant_need(row, et0, rain_mm, drip) for pid, row in garden.plants.iterrows()}
    soil = garden.soil.loc[profile["governorate"]]
    return {"garden_m2": float(garden_m2), "supply": supply, "need": need, "et0": et0, "rain_mm": rain_mm,
            "humidity": garden.humidity.loc[profile["governorate"], MONTHS].astype(float).tolist(),
            "soil": {"texture": soil["texture"], "ph": float(soil["ph"]), "sand": float(soil["sand_pct"]),
                     "silt": float(soil["silt_pct"]), "clay": float(soil["clay_pct"]),
                     "km_from_point": float(soil["km_from_point"])}}


def peak_week(series):
    """Highest litres per week across the months of a monthly series."""
    return max(per_week(v, m) for m, v in enumerate(series))


def budget_week(ctx):
    """The garden's weekly water in its driest month: the number a plan has to fit under."""
    return min(per_week(v, m) for m, v in enumerate(ctx["supply"]))


def garden_demand(picks, ctx):
    """Litres per month for a list of (plant_id, count) or GardenPick."""
    pairs = [(p.plant_id, p.count) if isinstance(p, GardenPick) else p for p in picks]
    return [sum(n * ctx["need"][pid][m] for pid, n in pairs) for m in range(len(MONTHS))]


def garden_area(picks, garden):
    pairs = [(p.plant_id, p.count) if isinstance(p, GardenPick) else p for p in picks]
    return sum(n * float(garden.plants.at[pid, "canopy_m2"]) for pid, n in pairs)


def short_months(demand, supply):
    return [m for m in range(len(MONTHS)) if demand[m] > supply[m] + 1e-9]


class GardenPick(BaseModel):
    model_config = STRICT
    plant_id: str
    count: int = Field(ge=1, le=GARDEN_COUNT_MAX)
    reason: str = Field(max_length=REASON_MAX)


class GardenPlan(BaseModel):
    model_config = STRICT
    language: Literal["en", "ar"]
    summary: str = Field(min_length=1)
    plants: list[GardenPick] = Field(max_length=GARDEN_KINDS_MAX)
    care_steps: list[str] = Field(min_length=GARDEN_STEPS, max_length=GARDEN_STEPS)


def validate_garden(raw, ctx, garden, plants, lang=None):
    """Parse and check a garden plan. Returns (GardenPlan, None) or (None, Rejection).

    Rejection details are written for the model: generate_garden sends the last one back so it can fix the plan.
    """
    raw, why = parse_reply(raw)
    if why:
        return None, why
    try:
        plan = GardenPlan.model_validate(raw)
    except ValidationError as e:
        errs = e.errors()
        q = next((err for err in errs if "count" in err["loc"]), None)
        if q:
            return None, Rejection(BAD_QUANTITY, f"count must be 1 to {GARDEN_COUNT_MAX}")
        return None, Rejection(SCHEMA, f"{'.'.join(map(str, errs[0]['loc']))}: {errs[0]['msg']}")
    if lang and plan.language != lang:
        return None, Rejection(WRONG_LANGUAGE, f"write in {lang}, not {plan.language}")
    if not plan.plants:
        return None, Rejection(EMPTY_GARDEN, "choose at least one plant")
    seen = set()
    unsafe = set(plants.loc[~plants["greywater_ok"], "plant_id"])
    for p in plan.plants:
        if p.plant_id in seen:
            return None, Rejection(DUPLICATE_PLANT, f"{shown_id(p.plant_id)} is listed twice; give it one count")
        seen.add(p.plant_id)
        if p.plant_id in unsafe:
            return None, Rejection(PLANT_NOT_GREYWATER_SAFE, f"{shown_id(p.plant_id)} is eaten raw and cannot take greywater")
        if p.plant_id not in garden.plants.index:
            return None, Rejection(UNKNOWN_PLANT, f"{shown_id(p.plant_id)} is not on the plant list")
    if (area := garden_area(plan.plants, garden)) > ctx["garden_m2"]:
        return None, Rejection(GARDEN_TOO_BIG, f"the plants cover {area:.0f} m² but the garden is {ctx['garden_m2']:.0f} m²")
    demand = garden_demand(plan.plants, ctx)
    if short := short_months(demand, ctx["supply"]):
        m = max(short, key=lambda i: demand[i] - ctx["supply"][i])
        return None, Rejection(GARDEN_SHORT, f"{MONTHS[m]} needs {per_week(demand[m], m):.0f} L/week but only "
                                             f"{per_week(ctx['supply'][m], m):.0f} L/week is available")
    text = " \n ".join([plan.summary, *plan.care_steps, *(p.reason for p in plan.plants)])
    if term := find_banned(text):
        return None, Rejection(BANNED_TERM, f"do not mention '{term}'")
    if (share := foreign_share(text, plan.language)) > SCRIPT_MAX_FOREIGN:
        return None, Rejection(WRONG_SCRIPT, f"{share:.0%} of letters are not {plan.language}")
    return plan, None


def build_garden_prompt(ctx, garden, lang, wishes="", feedback=None):
    """Short on purpose: on a CPU every word in and out costs time. Fixed text and the plant table come first so
    Ollama reuses the cached prefix; the household comes last. The water is one budget (the driest week) and each
    plant's peak need, so the model can add a plan up instead of guessing and being sent back."""
    table = "\n".join(f"{pid} {row['canopy_m2']:g} {peak_week(ctx['need'][pid]):.0f}"
                      for pid, row in garden.plants.iterrows())
    soil, rh = ctx["soil"], ctx["humidity"]
    language = "Modern Standard Arabic" if lang == "ar" else "plain English"
    wishes = " ".join(wishes.split())[:WISHES_MAX] or "none"
    retry = f"\nLast plan rejected: {feedback}. Fix it." if feedback else ""
    return f"""Plan a home garden in Jordan watered by greywater. Reply with one line of JSON matching the schema, language "{lang}", all text in {language}.
Rules: 1 to {GARDEN_KINDS_MAX} plant_ids from the table, each once. Sum of count x L/week must stay under the water budget; sum of count x m2 under the garden size. Prefer plants that suit the soil and the wishes. summary under 15 words, {GARDEN_STEPS} care_steps under 10 words each, each reason under 8 words. Do not mention water quality or safety.
plant_id m2 L/week
{table}
Soil: {soil['texture']}, pH {soil['ph']:g}. Humidity: {rh[6]:.0f}% in July, {rh[0]:.0f}% in January.
Water budget: {budget_week(ctx):.0f} L/week. Garden: {ctx['garden_m2']:g} m2.
Wishes: {wishes}{retry}"""


class GardenGeneration(NamedTuple):
    plan: "GardenPlan | None"  # None when no model was asked or none of its plans passed
    source: Literal["model", "none"]
    trace: list  # one dict per attempt: attempt, outcome (passed/rejected/error), code, detail


def generate_garden(ctx, garden, plants, lang, model, wishes="", chat=None):
    """Ask the model for a garden and check it. A rejected plan goes back to the model with the reason, up to
    MAX_ATTEMPTS calls; transport errors stop at once. Plant suggestions only ever come from the model: with no
    model, or no passing plan, the result has no plan. Never raises for the model."""
    chat = chat or (openrouter_chat if is_cloud(model) else ollama_chat)
    trace, feedback = [], None
    if model:
        schema = GardenPlan.model_json_schema()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw = chat(model, build_garden_prompt(ctx, garden, lang, wishes, feedback), schema)
            except Exception as e:  # noqa: BLE001 - every failure must end in the template
                err = as_model_error(e)
                trace.append({"attempt": attempt, "outcome": "error", "code": err.code, "detail": str(err)})
                log.info("garden attempt %d failed: %s", attempt, err.code)
                if err.retry:
                    continue
                break
            plan, why = validate_garden(raw, ctx, garden, plants, lang)
            if plan:
                trace.append({"attempt": attempt, "outcome": "passed", "code": "", "detail": ""})
                return GardenGeneration(plan, "model", trace)
            trace.append({"attempt": attempt, "outcome": "rejected", "code": why.code, "detail": why.detail})
            log.info("garden attempt %d rejected: %s", attempt, why.code)
            feedback = why.detail or why.code
    return GardenGeneration(None, "none", trace)


def garden_checks(plan, ctx, garden):
    """Checks shown on the garden badge. Returns list of (rule, passed)."""
    demand = garden_demand(plan.plants, ctx)
    return [
        ("Every plant is on the greywater-safe list", all(p.plant_id in garden.plants.index for p in plan.plants)),
        ("Plants fit the garden area", garden_area(plan.plants, garden) <= ctx["garden_m2"]),
        ("Enough water in every month", not short_months(demand, ctx["supply"])),
        ("No banned terms in generated text", find_banned(" ".join([plan.summary, *plan.care_steps])) is None),
        ("Fixed warnings and disclaimer attached", bool(WARNINGS[plan.language]) and bool(DISCLAIMER[plan.language])),
    ]


# Code-owned watering pattern by soil texture: how often to run the drip, not how much (that is the plan's job).
SOIL_GROUPS = {"sand": "sandy", "loamy sand": "sandy", "sandy loam": "sandy",
               "loam": "loamy", "silt loam": "loamy", "silt": "loamy",
               "sandy clay loam": "clayey", "clay loam": "clayey", "silty clay loam": "clayey",
               "sandy clay": "clayey", "silty clay": "clayey", "clay": "clayey"}
WATERING_NOTE = {
    "sandy": {"en": "Sandy soil drains fast: run the drip for short spells, every day or two in summer.",
              "ar": "التربة الرملية تصرّف الماء بسرعة: شغّل التنقيط لفترات قصيرة، كل يوم أو يومين في الصيف."},
    "loamy": {"en": "Loam holds water well: run the drip every two to three days in summer.",
              "ar": "التربة الطميية تحفظ الماء جيداً: شغّل التنقيط كل يومين إلى ثلاثة أيام في الصيف."},
    "clayey": {"en": "Clay soil holds water but takes it in slowly: run the drip longer and less often, every three to four days in summer, so it soaks in instead of pooling.",
               "ar": "التربة الطينية تحفظ الماء لكنها تمتصه ببطء: شغّل التنقيط مدة أطول وبتكرار أقل، كل ثلاثة إلى أربعة أيام في الصيف، ليتسرّب بدل أن يتجمّع."},
}


def watering_note(texture, lang):
    return WATERING_NOTE[SOIL_GROUPS.get(texture, "loamy")][lang]


SALT_NOTE = {"en": "Salt-sensitive: now and then water it with rain-tank water to wash laundry salts past the roots.",
             "ar": "حساسة للملوحة: اسقها أحياناً من خزان المطر لتغسل أملاح الغسيل بعيداً عن الجذور."}


def garden_notice(gen, model, lang):
    """On-screen notice when there is no garden to show, or None for a model garden."""
    if gen.source == "model":
        return None
    if not model:
        return {"en": "Describe what you want and press Design my garden. The plant suggestions come from the AI.",
                "ar": "اكتب ما تريده واضغط «صمّم حديقتي». اقتراحات النباتات تأتي من الذكاء الاصطناعي."}[lang]
    return {"en": f"{model} could not design a garden that passed the checks. Try again, change your wishes, or pick another model.",
            "ar": f"لم يستطع {model} تصميم حديقة تجتاز الفحوص. حاول مجدداً، أو غيّر رغباتك، أو اختر نموذجاً آخر."}[lang]
