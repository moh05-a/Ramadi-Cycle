"""Ramadi-Cycle local JSON API for the React frontend. Run: python api.py

Wraps ramadi.py only. Every number, price, plan and warning comes from there; this file adds no logic.
Listens on 127.0.0.1, so nothing outside this laptop can reach it.
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

# Same ranges as the Streamlit sliders in app.py.
LIMITS = {"roof_m2": (0, 400), "people": (1, 12), "showers_pp": (0, 14), "laundry_loads": (0, 14),
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

    @field_validator("governorate")
    @classmethod
    def known_governorate(cls, v):
        if v not in RAIN_MM:
            raise ValueError(f"unknown governorate: {v}")
        return v


def options():
    return {"governorates": [{"name": g, "rain_mm": mm} for g, mm in RAIN_MM.items()],
            "limits": LIMITS, "budgets": BUDGETS}


def plan(req: PlanRequest):
    profile = {"governorate": req.governorate, "rain_mm": RAIN_MM[req.governorate], "roof_m2": req.roof_m2,
               "people": req.people, "showers_pp": req.showers_pp, "laundry_loads": req.laundry_loads,
               "capacity_m3": req.capacity_m3, "year": req.year}
    res = r.simulate(profile, SHARES, A)
    blueprints = {b: r.template_blueprint(profile, b, req.lang) for b in BUDGETS}
    boms = {b: r.price(bp, CATALOG) for b, bp in blueprints.items()}
    bp, bom = blueprints[req.budget], boms[req.budget]
    cost = float(bom["total_jod"].sum())
    name_col = "name_ar" if req.lang == "ar" else "name_en"
    return {
        "profile": profile,
        "result": {k: float(res[k]) for k in ("potential", "rain_used", "greywater", "water", "overflow")}
                  | {"dry_months": res["dry_months"]},
        "impact": r.impact(res["water"], cost, A),
        "assumptions": A,
        "plan": {
            "source": "template",
            "language": bp.language,
            "summary": bp.summary,
            "rainwater_steps": bp.rainwater_steps,
            "greywater_steps": bp.greywater_steps,
            "plants": [{"plant_id": p.plant_id, "name": PLANT_NAMES.at[p.plant_id, name_col], "reason": p.reason}
                       for p in bp.plants],
            "bom": bom.drop(columns="why").to_dict("records"),
            "cost": cost,
        },
        "budget_costs": {b: float(boms[b]["total_jod"].sum()) for b in BUDGETS},
        "warnings": r.WARNINGS[req.lang],
        "disclaimer": r.DISCLAIMER[req.lang],
        "markdown": r.to_markdown(bp, bom, profile, res),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/options":
            return self.send(200, options())
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/plan":
            return self.send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1 << 16:
            return self.send(413, {"error": "request too large"})
        try:
            req = PlanRequest.model_validate_json(self.rfile.read(length))
        except ValidationError as e:
            err = e.errors()[0]
            return self.send(422, {"error": f"{'.'.join(map(str, err['loc']))}: {err['msg']}"})
        self.send(200, plan(req))

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
