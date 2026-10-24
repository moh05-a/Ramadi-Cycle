"""Ramadi-Cycle local JSON API for the React frontend. Run: python api.py

Wraps ramadi.py only. Every number, price, plan and warning comes from there; this file adds no logic.
Listens on 127.0.0.1, so nothing outside this laptop can reach it.

GET  /api/options   inputs, limits, installed models, method details and every data table
POST /api/plan      engine results, Sareef, community and the template plan (instant)
POST /api/generate  the same request plus "model": asks the local model, falls back to the template
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

import ramadi as r

RAIN, SHARES, CATALOG, PLANTS, ASSUMPTIONS = r.load_tables()
A = r.assumption_values(ASSUMPTIONS)
RAIN_MM = dict(zip(RAIN["governorate"], RAIN["annual_mm"].astype(float)))
PLANT_NAMES = PLANTS.set_index("plant_id")
BUDGETS = ["low", "full"]
MAX_BODY = 1 << 16

# Same ranges as the Streamlit sliders in app.py.
LIMITS = {"roof_m2": (0, 400), "people": (0, 12), "showers_pp": (0, 14), "laundry_loads": (0, 14),
          "capacity_m3": (0.5, 10.0)}


def _range(key):
    lo, hi = LIMITS[key]
    return Field(ge=lo, le=hi)


class PlanRequest(BaseModel):
    governorate: str
    roof_m2: float = _range("roof_m2")
    people: int = _range("people")
    showers_pp: int = _range("showers_pp")
    laundry_loads: int = _range("laundry_loads")
    capacity_m3: float = _range("capacity_m3")
    budget: Literal["low", "full"] = "low"
    lang: Literal["en", "ar"] = "en"
    year: Literal["dry", "average", "wet"] = "average"
    homes: int = Field(1, ge=1, le=r.COMMUNITY_MAX_HOMES)

    @field_validator("governorate")
    @classmethod
    def known_governorate(cls, v):
        if v not in RAIN_MM:
            raise ValueError(f"unknown governorate: {v}")
        return v


class GenerateRequest(PlanRequest):
    model: str = Field(min_length=1)


def _records(df):
    return df.to_dict("records")


def options():
    return {
        "governorates": [{"name": g, "rain_mm": mm} for g, mm in RAIN_MM.items()],
        "limits": LIMITS,
        "budgets": BUDGETS,
        "years": list(r.YEARS),
        "models": r.list_models(),
        "community_max": r.COMMUNITY_MAX_HOMES,
        "method": {
            "warnings": r.WARNINGS,
            "banned_terms": r.BANNED_TERMS,
            "allowed_phrases": r.ALLOWED_PHRASES,
            "required_items": r.REQUIRED_ITEMS,
            "max_attempts": r.MAX_ATTEMPTS,
            "quantity": [r.QTY_MIN, r.QTY_MAX],
            "schema": r.Blueprint.model_json_schema(),
            "ollama_url": r.OLLAMA_URL,
        },
        "tables": {
            "assumptions": _records(ASSUMPTIONS),
            "rainfall": _records(RAIN),
            "monthly_share": _records(r.read_table("monthly_share.csv")),
            "catalog": _records(CATALOG),
            "plants": _records(PLANTS),
        },
    }


def _profile(req):
    profile = {"governorate": req.governorate, "rain_mm": RAIN_MM[req.governorate], "roof_m2": req.roof_m2,
               "people": req.people, "showers_pp": req.showers_pp, "laundry_loads": req.laundry_loads,
               "capacity_m3": req.capacity_m3, "year": req.year}
    return profile, r.simulate(profile, SHARES, A)


def _plan_block(bp, source, notes, notice, profile, res, homes, budget):
    """Priced, safety-checked plan plus impact. Payback uses the standard parts list, never the model's picks."""
    bom = r.price(bp, CATALOG)
    cost = r.plan_cost(bom)
    std_cost = r.system_cost(profile, budget, CATALOG)
    imp = r.impact(res["water"], std_cost, A)
    name_col = "name_ar" if bp.language == "ar" else "name_en"
    return {
        "plan": {
            "source": source,
            "notes": notes,
            "notice": notice,
            "checks": [{"rule": rule, "passed": ok} for rule, ok in r.safety_checks(bp)],
            "language": bp.language,
            "summary": bp.summary,
            "rainwater_steps": bp.rainwater_steps,
            "greywater_steps": bp.greywater_steps,
            "plants": [{"plant_id": p.plant_id, "name": PLANT_NAMES.at[p.plant_id, name_col], "reason": p.reason}
                       for p in bp.plants],
            "bom": _records(bom),
            "cost": cost,
        },
        "impact": imp,
        "payback_cost": std_cost,
        "payback": r.format_payback(imp["payback_months"]),
        "community": r.community(res, imp, homes),
        "markdown": r.to_markdown(bp, bom, profile, res),
    }


def plan(req: PlanRequest):
    profile, res = _profile(req)
    blueprints = {b: r.template_blueprint(profile, b, req.lang) for b in BUDGETS}
    bp = blueprints[req.budget]
    return {
        "profile": profile,
        "result": {k: float(res[k]) for k in ("potential", "rain_used", "greywater", "water", "overflow")}
                  | {"dry_months": res["dry_months"]},
        "balance": _records(res["balance"]),
        "sareef": r.sareef(res, A, after=True),
        "assumptions": A,
        **_plan_block(bp, "template", [], None, profile, res, req.homes, req.budget),
        "budget_costs": {b: r.plan_cost(r.price(blueprints[b], CATALOG)) for b in BUDGETS},
        "warnings": r.WARNINGS[req.lang],
        "disclaimer": r.DISCLAIMER[req.lang],
        "prompt": r.build_prompt(profile, res, CATALOG, PLANTS, req.budget, req.lang),
    }


def generate(req: GenerateRequest, chat=None):
    """Ask the local model for a plan. Every failure ends in the template plan with notes saying why."""
    profile, res = _profile(req)
    gen = r.generate(profile, res, CATALOG, PLANTS, req.budget, req.lang, req.model, chat=chat,
                     max_total_jod=r.budget_cap(A, req.budget))
    return {"model": req.model,
            **_plan_block(gen.blueprint, gen.source, gen.notes, r.fallback_notice(gen, req.model), profile, res, req.homes,
                         req.budget)}


ROUTES = {"/api/plan": (PlanRequest, plan), "/api/generate": (GenerateRequest, generate)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/options":
            return self.send(200, options())
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ROUTES:
            return self.send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self.send(400, {"error": "bad Content-Length"})
        if length < 0:
            return self.send(400, {"error": "bad Content-Length"})
        if length > MAX_BODY:
            return self.send(413, {"error": "request too large"})
        model, handler = ROUTES[self.path]
        try:
            req = model.model_validate_json(self.rfile.read(length))
        except ValidationError as e:
            err = e.errors()[0]
            return self.send(422, {"error": f"{'.'.join(map(str, err['loc']))}: {err['msg']}"})
        try:
            body = handler(req)
        except r.InputError as e:
            return self.send(422, {"error": str(e)})
        self.send(200, body)

    def send(self, code, body):
        data = json.dumps(body, ensure_ascii=False, default=float).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(port):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    port = int(os.environ.get("RAMADI_API_PORT", 8000))
    print(f"Ramadi-Cycle API on http://127.0.0.1:{port}")
    serve(port).serve_forever()
