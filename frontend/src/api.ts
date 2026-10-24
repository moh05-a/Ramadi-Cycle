// Mirrors api.py. Every number, plan line and warning comes from ramadi.py through it.
import type { Lang } from "@brand";

export type Budget = "low" | "full";
export type FieldKey = "roof_m2" | "people" | "showers_pp" | "laundry_loads" | "capacity_m3";

export type Options = {
  governorates: { name: string; rain_mm: number }[];
  limits: Record<FieldKey, [number, number]>;
  budgets: Budget[];
};

export type PlanRequest = Record<FieldKey, number> & { governorate: string; budget: Budget; lang: Lang };

export type PlanResponse = {
  profile: { governorate: string; rain_mm: number; roof_m2: number; people: number };
  result: { potential: number; rain_used: number; greywater: number; water: number; overflow: number; dry_months: number };
  impact: { trips: number; jod: number; co2: number; payback_months: number | null };
  assumptions: Record<string, number>;
  plan: {
    source: "template";
    language: Lang;
    summary: string;
    rainwater_steps: string[];
    greywater_steps: string[];
    plants: { plant_id: string; name: string; reason: string }[];
    bom: { item: string; qty: number; unit: string; unit_jod: number; total_jod: number }[];
    cost: number;
  };
  budget_costs: Record<Budget, number>;
  warnings: string[];
  disclaimer: string;
  markdown: string;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? res.statusText);
  return body as T;
}

export const getOptions = () => call<Options>("/api/options");

export const getPlan = (req: PlanRequest, signal?: AbortSignal) =>
  call<PlanResponse>("/api/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
