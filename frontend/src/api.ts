// Mirrors api.py. Every number, plan line and warning comes from ramadi.py through it.
import type { Lang } from "@brand";

export type Budget = "low" | "full";
export type Year = "dry" | "average" | "wet";
export type FieldKey = "roof_m2" | "people" | "showers_pp" | "laundry_loads" | "capacity_m3";
export type TableKey = "assumptions" | "rainfall" | "monthly_share" | "catalog" | "plants";
type Row = Record<string, string | number | boolean>;

export type Options = {
  governorates: { name: string; rain_mm: number }[];
  limits: Record<FieldKey, [number, number]>;
  budgets: Budget[];
  years: Year[];
  models: string[];
  community_max: number;
  method: {
    warnings: Record<Lang, string[]>;
    banned_terms: string[];
    allowed_phrases: string[];
    required_items: string[];
    max_attempts: number;
    quantity: [number, number];
    schema: unknown;
    ollama_url: string;
  };
  tables: Record<TableKey, Row[]>;
};

export type PlanRequest = Record<FieldKey, number> & { governorate: string; budget: Budget; lang: Lang; year: Year; homes: number };

type Impact = { trips: number; jod: number; co2: number; payback_months: number | null };
type Trio = { trips: number; jod: number; co2: number };

export type Plan = {
  source: "template" | "model";
  notes: string[];
  notice: string | null;
  checks: { rule: string; passed: boolean }[];
  language: Lang;
  summary: string;
  rainwater_steps: string[];
  greywater_steps: string[];
  plants: { plant_id: string; name: string; reason: string }[];
  bom: { item: string; qty: number; unit: string; unit_jod: number; total_jod: number; why: string }[];
  cost: number;
};

/** The part of a response that depends on which plan is shown (template or model). */
export type PlanBlock = {
  plan: Plan;
  impact: Impact;
  payback_cost: number; // standard parts list for the budget; payback never uses the model's picks
  payback: string;
  community: { homes: number; water: number; trips: number; co2_t: number };
  markdown: string;
};

export type PlanResponse = PlanBlock & {
  profile: { governorate: string; rain_mm: number; roof_m2: number; people: number; capacity_m3: number; year: Year };
  result: { potential: number; rain_used: number; greywater: number; water: number; overflow: number; dry_months: number };
  balance: { month: string; start: number; inflow: number; demand: number; met: number; shortfall: number; overflow: number; level: number }[];
  sareef: { before: Trio; now: Trio; delta: Trio };
  assumptions: Record<string, number>;
  budget_costs: Record<Budget, number>;
  warnings: string[];
  disclaimer: string;
  prompt: string;
};

export type GenerateResponse = PlanBlock & { model: string };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? res.statusText);
  return body as T;
}

const post = <T,>(path: string, body: unknown, signal?: AbortSignal) =>
  call<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });

export const getOptions = () => call<Options>("/api/options");
export const getPlan = (req: PlanRequest, signal?: AbortSignal) => post<PlanResponse>("/api/plan", req, signal);
export const generatePlan = (req: PlanRequest & { model: string }, signal?: AbortSignal) =>
  post<GenerateResponse>("/api/generate", req, signal);
