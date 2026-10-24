import { useEffect, useId, useState } from "react";
import { Button, Mark, Notice, Warning, num, type Lang } from "@brand";
import { getOptions, getPlan, type Budget, type FieldKey, type Options, type PlanResponse } from "./api";
import { COPY } from "./copy";

const FIELDS: FieldKey[] = ["roof_m2", "people", "showers_pp", "laundry_loads", "capacity_m3"];
const INTEGER: FieldKey[] = ["people", "showers_pp", "laundry_loads"];
const START: Record<FieldKey, string> = { roof_m2: "120", people: "5", showers_pp: "5", laundry_loads: "4", capacity_m3: "2" };

/** Parse a typed value and pull it into the API's allowed range. */
function clampField(key: FieldKey, raw: string, [lo, hi]: [number, number]) {
  const x = parseFloat(raw);
  const n = Number.isFinite(x) ? (INTEGER.includes(key) ? Math.round(x) : x) : lo;
  const value = Math.min(hi, Math.max(lo, n));
  return { value, adjusted: raw.trim() !== "" && value !== x };
}

export function App() {
  const [lang, setLang] = useState<Lang>("ar");
  const [options, setOptions] = useState<Options>();
  const [gov, setGov] = useState("");
  const [form, setForm] = useState(START);
  const [budget, setBudget] = useState<Budget>("low");
  const [data, setData] = useState<PlanResponse>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const t = COPY[lang];

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  useEffect(() => {
    getOptions()
      .then((o) => { setOptions(o); setGov((g) => g || o.governorates[0].name); setError(""); })
      .catch((e: Error) => setError(e.message));
  }, [attempt]);

  const fields = options && Object.fromEntries(FIELDS.map((k) => [k, clampField(k, form[k], options.limits[k])])) as
    Record<FieldKey, { value: number; adjusted: boolean }> | undefined;
  const reqKey = fields && gov ? JSON.stringify({ gov, budget, lang, ...Object.fromEntries(FIELDS.map((k) => [k, fields[k].value])) }) : "";

  useEffect(() => {
    if (!fields || !gov) return;
    const ctl = new AbortController();
    const timer = setTimeout(() => {
      getPlan({ governorate: gov, budget, lang, ...Object.fromEntries(FIELDS.map((k) => [k, fields[k].value])) as Record<FieldKey, number> }, ctl.signal)
        .then((d) => { setData(d); setError(""); })
        .catch((e: Error) => { if (e.name !== "AbortError") setError(e.message); });
    }, 150);
    return () => { clearTimeout(timer); ctl.abort(); };
  }, [reqKey, attempt]); // reqKey captures every input that changes the request

  const download = () => {
    if (!data) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([data.markdown], { type: "text/markdown" }));
    a.download = `ramadi-plan-${data.plan.language}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="rc-root app" dir={lang === "ar" ? "rtl" : "ltr"} lang={lang}>
      <header className="app-header">
        <div className="app-wrap app-header__row">
          <div className="app-brand">
            <Mark size={40} title="" />
            <span className="app-brand__main">{t.brand}</span>
            <span className="app-brand__sub" lang={lang === "ar" ? "en" : "ar"}>{t.brand2}</span>
          </div>
          <button type="button" className="app-lang noprint" lang={lang === "ar" ? "en" : "ar"}
            onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            <span aria-hidden="true" />{t.otherLang}
          </button>
        </div>
      </header>

      <section className="app-hero">
        <div className="app-wrap">
          <h1>{t.title}</h1>
          <p>{t.intro}</p>
        </div>
      </section>

      <main className="app-wrap app-main">
        {error && (
          <div className="app-error noprint">
            <Notice>
              {t.offline} <code dir="ltr">python api.py</code>
              <span className="app-error__detail" dir="ltr">({error})</span>
            </Notice>
            <Button variant="secondary" onClick={() => setAttempt((n) => n + 1)}>{t.retry}</Button>
          </div>
        )}

        <section className="app-panel app-form noprint" aria-labelledby="h-step1">
          <div className="app-panel__head"><h2 id="h-step1">{t.step1}</h2></div>
          <div className="app-panel__body app-form__body">
            <GovField label={t.gov} value={gov} onChange={setGov} options={options?.governorates ?? []} />
            {FIELDS.map((k) => (
              <NumberField key={k} {...t.fields[k]} value={form[k]} onChange={(v) => setForm({ ...form, [k]: v })}
                warning={fields?.[k].adjusted && options ? t.range(...options.limits[k]) : undefined} />
            ))}
            <fieldset className="app-budget">
              <legend>{t.budget}</legend>
              {(options?.budgets ?? []).map((b) => (
                <label key={b} className="app-budget__opt">
                  <input type="radio" name="budget" value={b} checked={budget === b} onChange={() => setBudget(b)} />
                  <span className="app-budget__text">
                    <b>{t.budgets[b][0]}</b>
                    <span>{t.budgets[b][1].replace("{c}", data ? num(data.budget_costs[b]) : "…")}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          </div>
        </section>

        <div className="app-results" aria-live="polite" aria-busy={!data}>
          {data ? <Results data={data} lang={lang} onDownload={download} /> : !error && <p className="app-loading">{t.loading}</p>}
        </div>
      </main>
    </div>
  );
}

function GovField({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: Options["governorates"] }) {
  const id = useId();
  return (
    <div className="app-field">
      <label htmlFor={id}>{label}</label>
      {/* Names come from data/rainfall.csv, which only has English names. */}
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} dir="auto">
        {options.map((g) => <option key={g.name} value={g.name}>{g.name}</option>)}
      </select>
    </div>
  );
}

type NumberFieldProps = { label: string; unit: string; hint?: string; warning?: string; value: string; onChange: (v: string) => void };

function NumberField({ label, unit, hint, warning, value, onChange }: NumberFieldProps) {
  const id = useId();
  const note = warning ?? hint;
  return (
    <div className="app-field">
      <label htmlFor={id}>{label}</label>
      <span className="app-input">
        <input id={id} type="number" inputMode="decimal" min={0} value={value} placeholder="0"
          onChange={(e) => onChange(e.target.value)} aria-describedby={note ? id + "-n" : undefined} />
        <span className="app-input__unit" dir="ltr">{unit}</span>
      </span>
      {note && <span id={id + "-n"} className={warning ? "app-field__warn" : "app-field__hint"}>{note}</span>}
    </div>
  );
}

function Results({ data, lang, onDownload }: { data: PlanResponse; lang: Lang; onDownload: () => void }) {
  const t = COPY[lang];
  const { result: res, impact: imp, plan, assumptions: a, profile } = data;
  const payback = imp.payback_months;
  const secondary = [
    { key: "trips", value: num(imp.trips, 1), unit: t.results.trips[1], cls: "" },
    { key: "water", value: num(res.water), unit: t.results.water[1], cls: "is-water" },
    { key: "pay", value: payback ? num(payback) : t.none, unit: payback ? t.results.pay[1] : "", cls: "" },
  ] as const;
  const details = t.detailLines({
    rainUsed: num(res.rain_used, 1), grey: num(res.greywater, 1), potential: num(res.potential, 1),
    overflow: num(res.overflow, 1), dry: num(res.dry_months), co2: num(imp.co2),
    tankerVolume: num(a.tanker_volume), tankerPrice: num(a.tanker_price), litres: num(a.nonpotable_litres_per_person_day),
  });

  return (
    <>
      <section className="app-panel" aria-labelledby="h-step2">
        <div className="app-panel__head is-dark">
          <h2 id="h-step2">{t.step2}</h2>
          <span>{t.line(profile.governorate, num(profile.rain_mm), num(profile.roof_m2), num(profile.people))}</span>
        </div>
        <div className="app-headline">
          <span className="app-headline__label">{t.results.jod[0]}</span>
          <span className="app-headline__row">
            <span className="app-headline__value">{num(imp.jod)}</span>
            <span className="app-headline__unit">{t.results.jod[1]}</span>
          </span>
        </div>
        <div className="app-secondary">
          {secondary.map((s) => (
            <div key={s.key} className="app-secondary__cell">
              <span className="app-secondary__label">{t.results[s.key][0]}</span>
              <span className="app-secondary__row">
                <span className={`app-secondary__value ${s.cls}`}>{s.value}</span>
                <span className="app-secondary__unit">{s.unit}</span>
              </span>
            </div>
          ))}
        </div>
        <div className="app-panel__foot">{t.estimateNote}</div>
      </section>

      <section className="app-panel" aria-labelledby="h-step3">
        <div className="app-panel__head">
          <h2 id="h-step3">{t.step3}</h2>
          <p>{plan.summary}</p>
        </div>
        <div className="app-panel__body app-plan">
          <div className="app-steps-grid">
            <Steps title={t.rain} steps={plan.rainwater_steps} tone="rain" />
            <Steps title={t.grey} steps={plan.greywater_steps} tone="grey" />
          </div>

          <div>
            <h3 className="app-h3">{t.materials}</h3>
            <div className="rc-table-wrap" tabIndex={0} role="region" aria-label={t.materials}>
              <table className="rc-table app-bom">
                <thead><tr><th scope="col">{t.colItem}</th><th scope="col">{t.colQty}</th><th scope="col">{t.jod}</th></tr></thead>
                <tbody>
                  {plan.bom.map((row) => (
                    <tr key={row.item}><td>{row.item}</td><td>{num(row.qty)}</td><td>{num(row.total_jod)}</td></tr>
                  ))}
                </tbody>
                <tfoot><tr><th scope="row" colSpan={2}>{t.total}</th><td>{num(plan.cost)} {t.jod}</td></tr></tfoot>
              </table>
            </div>
            <p className="app-note">{t.pricesNote}</p>
          </div>

          <div>
            <h3 className="app-h3">{t.plants}</h3>
            <ul className="app-plants">
              {plan.plants.map((p) => <li key={p.plant_id}><span><b>{p.name}</b>: {p.reason}</span></li>)}
            </ul>
          </div>
        </div>

        <div className="app-safety">
          <h3 className="app-h3 app-safety__title">{t.safety}</h3>
          {data.warnings.map((w) => <Warning key={w}>{w}</Warning>)}
        </div>

        <div className="app-actions noprint">
          <Button onClick={() => window.print()}>{t.print}</Button>
          <Button variant="secondary" onClick={onDownload}>{t.download}</Button>
        </div>
      </section>

      <details className="app-panel app-details noprint">
        <summary>{t.details}</summary>
        <ul>{details.map((d) => <li key={d}>{d}</li>)}</ul>
      </details>

      <p className="app-disclaimer">{data.disclaimer}</p>
    </>
  );
}

function Steps({ title, steps, tone }: { title: string; steps: string[]; tone: "rain" | "grey" }) {
  return (
    <div className={`app-steps is-${tone}`}>
      <h3 className="app-h3">{title}</h3>
      <ol>{steps.map((s) => <li key={s}>{s}</li>)}</ol>
    </div>
  );
}
