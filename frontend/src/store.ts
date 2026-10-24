// App state shared by every page: options, inputs, the engine response and the AI plan.
import { useEffect, useRef, useState } from "react";
import type { Lang } from "@brand";
import {
  generatePlan, getOptions, getPlan,
  type Budget, type FieldKey, type GenerateResponse, type Options, type PlanBlock, type PlanResponse, type Year,
} from "./api";

export const FIELDS: FieldKey[] = ["roof_m2", "people", "showers_pp", "laundry_loads", "capacity_m3"];
const INTEGER: FieldKey[] = ["people", "showers_pp", "laundry_loads"];
const START: Record<FieldKey, string> = { roof_m2: "120", people: "5", showers_pp: "5", laundry_loads: "4", capacity_m3: "2" };

/** useState that survives a reload. Storage can be missing or blocked, so every access is guarded. */
export function useStored<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? initial : (JSON.parse(raw) as T);
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage blocked: keep in memory */ }
  }, [key, value]);
  return [value, setValue] as const;
}

/** Parse a typed value and pull it into the API's allowed range. */
export function clampField(key: FieldKey, raw: string, [lo, hi]: [number, number]) {
  const x = parseFloat(raw);
  const n = Number.isFinite(x) ? (INTEGER.includes(key) ? Math.round(x) : x) : lo;
  const value = Math.min(hi, Math.max(lo, n));
  return { value, adjusted: raw.trim() !== "" && value !== x };
}

type Generated = { key: string; res: GenerateResponse };

export function useRamadi() {
  const [lang, setLang] = useStored<Lang>("rc.lang", "ar");
  const [gov, setGov] = useStored("rc.gov", "");
  const [form, setForm] = useStored("rc.form", START);
  const [budget, setBudget] = useStored<Budget>("rc.budget", "low");
  const [year, setYear] = useStored<Year>("rc.year", "average");
  const [homes, setHomes] = useStored("rc.homes", 100);
  const [options, setOptions] = useState<Options>();
  const [model, setModel] = useState("");
  const [data, setData] = useState<PlanResponse>();
  const [generated, setGenerated] = useState<Generated>();
  const [generating, setGenerating] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const genCtl = useRef<AbortController>();

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  useEffect(() => {
    getOptions()
      .then((o) => {
        setOptions(o);
        // a stored governorate may have been removed from rainfall.csv
        setGov((g) => (o.governorates.some((x) => x.name === g) ? g : o.governorates[0].name));
        // privacy: preselect a local model only; a cloud model must be picked on purpose
        setModel((m) => m || o.models.find((x) => !x.startsWith("openrouter:")) || "");
        setError("");
      })
      .catch((e: Error) => setError(e.message));
  }, [attempt]);

  const fields = options && (Object.fromEntries(FIELDS.map((k) => [k, clampField(k, form[k] ?? START[k], options.limits[k])])) as
    Record<FieldKey, { value: number; adjusted: boolean }>);
  const values = fields && (Object.fromEntries(FIELDS.map((k) => [k, fields[k].value])) as Record<FieldKey, number>);
  // planKey: everything that changes the plan. The neighbourhood size doesn't, so it is left out.
  const planKey = values && gov ? JSON.stringify({ gov, budget, lang, year, ...values }) : "";
  const reqKey = planKey && `${planKey}|${homes}`;
  const request = () => ({ governorate: gov, budget, lang, year, homes, ...values! });

  useEffect(() => {
    if (!planKey) return;
    const ctl = new AbortController();
    const timer = setTimeout(() => {
      getPlan(request(), ctl.signal)
        .then((d) => { setData(d); setError(""); })
        .catch((e: Error) => { if (e.name !== "AbortError") setError(e.message); });
    }, 150);
    return () => { clearTimeout(timer); ctl.abort(); };
  }, [reqKey, attempt]); // reqKey captures every input that changes the request

  // A plan belongs to the inputs it was made for, and is only shown after the user asks for it.
  // Drop it (and stop a running request) when the inputs change.
  const [requested, setRequested] = useState<string>();
  useEffect(() => {
    const had = (generated && generated.key !== planKey) || (requested !== undefined && requested !== planKey);
    if (had) { setGenerated(undefined); setRequested(undefined); setStale(true); }
    if (generating) { genCtl.current?.abort(); setGenerating(false); }
  }, [planKey]);

  const writeWithAI = () => {
    if (!planKey || !model) return;
    const key = planKey;
    const ctl = new AbortController();
    genCtl.current = ctl;
    setGenerating(true);
    setStale(false);
    generatePlan({ ...request(), model }, ctl.signal)
      .then((res) => { setGenerated({ key, res }); setError(""); })
      .catch((e: Error) => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => { if (genCtl.current === ctl) setGenerating(false); });
  };

  const makeStandard = () => { setGenerated(undefined); setRequested(planKey); setStale(false); };
  const shown: PlanBlock | undefined =
    generated?.key === planKey ? generated.res : planKey && requested === planKey ? data : undefined;

  return {
    lang, setLang, options, error, retry: () => setAttempt((n) => n + 1), planKey, request,
    gov, setGov, form, setForm: (k: FieldKey, v: string) => setForm({ ...form, [k]: v }), fields,
    budget, setBudget, year, setYear, homes, setHomes,
    data, shown, isDefault: JSON.stringify(form) === JSON.stringify(START),
    ai: {
      model, setModel, generating, stale, isAI: !!shown && shown !== data,
      write: writeWithAI,
      cancel: () => { genCtl.current?.abort(); setGenerating(false); },
      reset: makeStandard, standard: makeStandard,
    },
  };
}

export type Store = ReturnType<typeof useRamadi>;
export type AI = Store["ai"];
