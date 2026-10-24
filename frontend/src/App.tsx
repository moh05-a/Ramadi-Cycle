import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Button, Mark, MonthlyBars, Notice, SafetyBadge, TankLine, Warning, num, type Lang } from "@brand";
import {
  generatePlan, getOptions, getPlan,
  type Budget, type FieldKey, type GenerateResponse, type Options, type PlanBlock, type PlanResponse, type TableKey, type Year,
} from "./api";
import { COPY } from "./copy";

const isCloud = (m: string) => m.startsWith("openrouter:");
const FIELDS: FieldKey[] = ["roof_m2", "people", "showers_pp", "laundry_loads", "capacity_m3"];
const INTEGER: FieldKey[] = ["people", "showers_pp", "laundry_loads"];
const START: Record<FieldKey, string> = { roof_m2: "120", people: "5", showers_pp: "5", laundry_loads: "4", capacity_m3: "2" };
const TABLES: TableKey[] = ["assumptions", "rainfall", "monthly_share", "catalog", "plants"];

/** Parse a typed value and pull it into the API's allowed range. */
function clampField(key: FieldKey, raw: string, [lo, hi]: [number, number]) {
  const x = parseFloat(raw);
  const n = Number.isFinite(x) ? (INTEGER.includes(key) ? Math.round(x) : x) : lo;
  const value = Math.min(hi, Math.max(lo, n));
  return { value, adjusted: raw.trim() !== "" && value !== x };
}

type Generated = { key: string; res: GenerateResponse };

export function App() {
  const [lang, setLang] = useState<Lang>("ar");
  const [options, setOptions] = useState<Options>();
  const [gov, setGov] = useState("");
  const [form, setForm] = useState(START);
  const [budget, setBudget] = useState<Budget>("low");
  const [year, setYear] = useState<Year>("average");
  const [homes, setHomes] = useState(100);
  const [model, setModel] = useState("");
  const [data, setData] = useState<PlanResponse>();
  const [generated, setGenerated] = useState<Generated>();
  const [generating, setGenerating] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const genCtl = useRef<AbortController>();
  const t = COPY[lang];

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  useEffect(() => {
    getOptions()
      .then((o) => {
        setOptions(o);
        setGov((g) => g || o.governorates[0].name);
        setModel((m) => m || o.models[0] || "");
        setError("");
      })
      .catch((e: Error) => setError(e.message));
  }, [attempt]);

  const fields = options && Object.fromEntries(FIELDS.map((k) => [k, clampField(k, form[k], options.limits[k])])) as
    Record<FieldKey, { value: number; adjusted: boolean }> | undefined;
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

  // An AI plan belongs to the inputs it was written for. Drop it (and stop a running request) when they change.
  useEffect(() => {
    if (generated && generated.key !== planKey) { setGenerated(undefined); setStale(true); }
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
  const cancelAI = () => { genCtl.current?.abort(); setGenerating(false); };

  const shown: PlanBlock | undefined = generated?.key === planKey ? generated.res : data;

  const download = () => {
    if (!shown) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([shown.markdown], { type: "text/markdown" }));
    a.download = `ramadi-plan-${shown.plan.language}.md`;
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
            <GovField label={t.gov} value={gov} onChange={setGov} options={options?.governorates ?? []} names={t.govNames} />
            {FIELDS.map((k) => (
              <NumberField key={k} {...t.fields[k]} value={form[k]} onChange={(v) => setForm({ ...form, [k]: v })}
                warning={fields?.[k].adjusted && options ? t.range(...options.limits[k]) : undefined} />
            ))}
            <fieldset className="app-choice">
              <legend>{t.year}</legend>
              <div className="app-choice__row">
                {(options?.years ?? []).map((y) => (
                  <label key={y} className="app-choice__opt">
                    <input type="radio" name="year" value={y} checked={year === y} onChange={() => setYear(y)} />
                    <span>{t.years[y]}</span>
                  </label>
                ))}
              </div>
              <span className="app-field__hint">{t.yearHint}</span>
            </fieldset>
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
          {data && shown && options ? (
            <Results data={data} shown={shown} options={options} lang={lang} year={year} homes={homes} setHomes={setHomes}
              ai={{ model, setModel, generating, stale, isAI: shown !== data, write: writeWithAI, cancel: cancelAI,
                    reset: () => setGenerated(undefined) }}
              onDownload={download} />
          ) : !error && <p className="app-loading">{t.loading}</p>}
        </div>
      </main>
    </div>
  );
}

function GovField({ label, value, onChange, options, names }: {
  label: string; value: string; onChange: (v: string) => void; options: Options["governorates"]; names: Record<string, string>;
}) {
  const id = useId();
  return (
    <div className="app-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((g) => <option key={g.name} value={g.name}>{names[g.name] ?? g.name}</option>)}
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

type AI = {
  model: string; setModel: (m: string) => void; generating: boolean; stale: boolean; isAI: boolean;
  write: () => void; cancel: () => void; reset: () => void;
};

type ResultsProps = {
  data: PlanResponse; shown: PlanBlock; options: Options; lang: Lang; year: Year;
  homes: number; setHomes: (n: number) => void; ai: AI; onDownload: () => void;
};

function Results({ data, shown, options, lang, year, homes, setHomes, ai, onDownload }: ResultsProps) {
  const t = COPY[lang];
  const { result: res, assumptions: a, profile } = data;
  const { impact: imp, plan } = shown;
  const payback = imp.payback_months;
  const govName = t.govNames[profile.governorate] ?? profile.governorate;
  const secondary = [
    { key: "trips", value: num(imp.trips, 1), unit: t.results.trips[1], cls: "" },
    { key: "water", value: num(res.water, 1), unit: t.results.water[1], cls: "is-water" },
    { key: "pay", value: payback == null ? t.none : num(payback), unit: payback == null ? "" : t.results.pay[1], cls: "" },
  ] as const;
  const details = t.detailLines({
    rainUsed: num(res.rain_used, 1), grey: num(res.greywater, 1), co2: num(imp.co2),
    tankerVolume: num(a.tanker_volume), tankerPrice: num(a.tanker_price), litres: num(a.nonpotable_litres_per_person_day),
  });

  return (
    <>
      <section className="app-panel" aria-labelledby="h-step2">
        <div className="app-panel__head is-dark">
          <h2 id="h-step2">{t.step2}</h2>
          <span>{t.line(govName, num(profile.rain_mm), num(profile.roof_m2), num(profile.people))}</span>
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
        <div className="app-panel__foot">{t.estimateNote(t.years[year])}</div>
      </section>

      <Impact data={data} lang={lang} homes={homes} setHomes={setHomes} max={options.community_max} />

      <section className="app-panel" aria-labelledby="h-step3">
        <div className="app-panel__head">
          <h2 id="h-step3">{t.step3}</h2>
          <p>{plan.summary}</p>
        </div>

        <AIBox ai={ai} plan={plan} models={options.models} lang={lang} />

        <div className="app-panel__body app-plan">
          <div className="app-checks">
            <SafetyBadge passed={plan.checks.filter((c) => c.passed).length} total={plan.checks.length} label={t.checksLabel} ofWord={t.of} />
            <ul>
              {plan.checks.map((c) => (
                <li key={c.rule} className={c.passed ? "is-pass" : "is-fail"}>
                  <span aria-hidden="true">{c.passed ? "✓" : "✕"}</span> {t.checkRules[c.rule] ?? c.rule}
                </li>
              ))}
            </ul>
          </div>

          <div className="app-steps-grid">
            <Steps title={t.rain} steps={plan.rainwater_steps} tone="rain" />
            <Steps title={t.grey} steps={plan.greywater_steps} tone="grey" />
          </div>

          <div>
            <h3 className="app-h3">{t.materials}</h3>
            <div className="rc-table-wrap" tabIndex={0} role="region" aria-label={t.materials}>
              <table className="rc-table app-bom">
                <thead><tr><th scope="col">{t.colItem}</th><th scope="col">{t.colQty}</th><th scope="col">{t.jod}</th><th scope="col">{t.colWhy}</th></tr></thead>
                <tbody>
                  {plan.bom.map((row, i) => (
                    <tr key={row.item + i}><td>{row.item}</td><td>{num(row.qty)}</td><td>{num(row.total_jod)}</td><td className="app-bom__why">{row.why}</td></tr>
                  ))}
                </tbody>
                <tfoot><tr><th scope="row" colSpan={2}>{t.total}</th><td colSpan={2}>{num(plan.cost)} {t.jod}</td></tr></tfoot>
              </table>
            </div>
            <p className="app-note">{t.pricesNote}</p>
            {Math.abs(plan.cost - shown.payback_cost) > 0.5 && <p className="app-note">{t.paybackNote(num(shown.payback_cost))}</p>}
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

      <Method data={data} options={options} lang={lang} model={ai.isAI ? ai.model : ""} />
      <Assumptions options={options} lang={lang} />

      <p className="app-disclaimer">{data.disclaimer}</p>
    </>
  );
}

function Impact({ data, lang, homes, setHomes, max }: { data: PlanResponse; lang: Lang; homes: number; setHomes: (n: number) => void; max: number }) {
  const t = COPY[lang];
  const [view, setView] = useState<"today" | "with">("with");
  const homesId = useId();
  const { result: res, sareef, community: com } = data;
  const now = view === "with" ? sareef.now : sareef.before;
  const rows = [
    { key: "trips" as const, d: 1 }, { key: "jod" as const, d: 0 }, { key: "co2" as const, d: 0 },
  ];
  return (
    <section className="app-panel" aria-labelledby="h-impact">
      <div className="app-panel__head"><h2 id="h-impact">{t.impact}</h2></div>
      <div className="app-panel__body app-impact">
        <div className="app-charts">
          <figure className="app-chart">
            <figcaption className="app-h3">{t.tankChart}</figcaption>
            <TankLine lang={lang} level={data.balance.map((m) => m.level)} capacity={data.profile.capacity_m3}
              label={t.tankChart} legend={t.tankLegend} />
          </figure>
          <figure className="app-chart">
            <figcaption className="app-h3">{t.demandChart}</figcaption>
            <MonthlyBars lang={lang} label={t.demandChart} series={[
              { label: t.fromRain, values: data.balance.map((m) => m.met), color: "cistern" },
              { label: t.bought, values: data.balance.map((m) => m.shortfall), color: "bought" },
            ]} />
          </figure>
          <p className="app-note">{t.chartSummary(num(res.dry_months), num(res.overflow, 1), num(res.rain_used, 1), num(res.potential, 1))}</p>
        </div>

        <div className="app-sareef">
          <h3 className="app-h3">{t.sareef} <span lang="ar">· صهريج</span></h3>
          <p className="app-note">{t.sareefSub}</p>
          <div className="app-seg" role="group" aria-label={t.sareef}>
            <button type="button" aria-pressed={view === "today"} onClick={() => setView("today")}>{t.today}</button>
            <button type="button" aria-pressed={view === "with"} onClick={() => setView("with")}>{t.withSystem}</button>
          </div>
          <dl className="app-sareef__rows">
            {rows.map(({ key, d }) => (
              <div key={key}>
                <dt>{t.sareefRows[key][0]}</dt>
                <dd>
                  <span className="app-sareef__value">{num(now[key], d)}</span> <span className="app-secondary__unit">{t.sareefRows[key][1]}</span>
                  {view === "with" && <span className="app-sareef__delta">↓ {num(Math.abs(sareef.delta[key]), d)}</span>}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="app-community">
          <h3 className="app-h3">{t.community}</h3>
          <label htmlFor={homesId} className="app-community__label">
            {t.homes} <output htmlFor={homesId}>{num(homes)}</output>
          </label>
          <input id={homesId} type="range" min={1} max={max} step={1} value={homes} onChange={(e) => setHomes(Number(e.target.value))} />
          <p>{t.communityLine(num(com.homes), num(com.water), num(com.trips), num(com.co2_t, 1))}</p>
        </div>
      </div>
    </section>
  );
}

function AIBox({ ai, plan, models, lang }: { ai: AI; plan: PlanBlock["plan"]; models: string[]; lang: Lang }) {
  const t = COPY[lang];
  const id = useId();
  let status: ReactNode;
  if (ai.isAI && plan.source === "model") status = <p className="app-ai__status is-ok">{t.byModel(ai.model)}</p>;
  else if (ai.isAI) status = (
    <Notice>
      {t.fallback(ai.model)}
      <details className="app-ai__why"><summary>{t.failDetails}</summary>
        <ul dir="ltr">{plan.notes.map((n) => <li key={n}><code>{n}</code></li>)}</ul>
      </details>
    </Notice>
  );
  else status = <p className="app-ai__status">{ai.stale ? t.stale : t.byTemplate}</p>;

  return (
    <div className="app-ai noprint">
      <div className="app-ai__head">
        <b>{t.aiTitle}</b>
        <span>{t.aiIntro}</span>
      </div>
      {models.length === 0 ? (
        <Notice>{t.noModels}</Notice>
      ) : (
        <div className="app-ai__controls">
          <div className="app-field">
            <label htmlFor={id}>{t.model}</label>
            <select id={id} value={ai.model} onChange={(e) => ai.setModel(e.target.value)} disabled={ai.generating} dir="ltr">
              {models.map((m) => <option key={m} value={m}>{isCloud(m) ? `${m.slice(11)} (${t.cloudTag})` : m}</option>)}
            </select>
          </div>
          {ai.generating
            ? <Button variant="secondary" onClick={ai.cancel}>{t.aiCancel}</Button>
            : <Button onClick={ai.write} disabled={!ai.model}>{t.aiButton}</Button>}
          {ai.isAI && !ai.generating && <Button variant="secondary" onClick={ai.reset}>{t.useTemplate}</Button>}
        </div>
      )}
      {isCloud(ai.model) && models.length > 0 && <Notice>{t.cloudNote}</Notice>}
      {ai.generating ? <p className="app-ai__status" role="status">{t.aiWorking(ai.model)}</p> : status}
    </div>
  );
}

function Method({ data, options, lang, model }: { data: PlanResponse; options: Options; lang: Lang; model: string }) {
  const t = COPY[lang];
  const m = options.method;
  return (
    <details className="app-panel app-details app-method noprint">
      <summary>{t.method}</summary>
      <div className="app-method__body">
        <h3 className="app-h3">{t.who}</h3>
        <div className="rc-table-wrap" tabIndex={0} role="region" aria-label={t.who}>
          <table className="rc-table"><tbody>{t.whoRows.map(([task, owner]) => <tr key={task}><td>{task}</td><td><b>{owner}</b></td></tr>)}</tbody></table>
        </div>

        <h3 className="app-h3">{t.rules}</h3>
        <div className="app-method__rules">{m.warnings[lang].map((w) => <Warning key={w}>{w}</Warning>)}</div>
        <p className="app-note">{t.retries(m.max_attempts, ...m.quantity)}</p>
        <p className="app-note">{t.banned}: <span dir="auto">{m.banned_terms.join(", ")}</span></p>
        <p className="app-note">{t.allowed}: <span dir="ltr">{m.allowed_phrases.join(", ")}</span></p>

        <h3 className="app-h3">{t.formulas}</h3>
        <pre dir="ltr" tabIndex={0}>{t.formulaLines.join("\n")}</pre>

        <h3 className="app-h3">{t.modelHeading}</h3>
        <p className="app-note">{model ? (isCloud(model) ? t.cloudLine(model.slice(11)) : t.modelLine(model, m.ollama_url)) : options.models.length ? t.modelLine(options.models.join(", "), m.ollama_url) : t.modelNone}</p>

        <details className="app-method__more"><summary>{t.schema}</summary>
          <pre dir="ltr" tabIndex={0}>{JSON.stringify(m.schema, null, 2)}</pre>
        </details>
        <details className="app-method__more"><summary>{t.prompt}</summary>
          <pre dir="ltr" tabIndex={0}>{data.prompt}</pre>
        </details>
      </div>
    </details>
  );
}

function Assumptions({ options, lang }: { options: Options; lang: Lang }) {
  const t = COPY[lang];
  const rows = options.tables.assumptions;
  const verified = rows.filter((r) => r.status === "verified").length;
  return (
    <details className="app-panel app-details app-method noprint">
      <summary>{t.data}</summary>
      <div className="app-method__body">
        <p className="app-note">{t.dataIntro(verified, rows.length)}</p>
        {TABLES.map((key) => {
          const table = options.tables[key];
          const cols = Object.keys(table[0] ?? {});
          return (
            <div key={key}>
              <h3 className="app-h3">{t.tables[key]}</h3>
              <div className="rc-table-wrap" tabIndex={0} role="region" aria-label={t.tables[key]}>
                <table className="rc-table app-data">
                  <thead><tr>{cols.map((c) => <th key={c} scope="col">{t.columns[c] ?? c.replace(/_/g, " ")}</th>)}</tr></thead>
                  <tbody>
                    {table.map((row, i) => (
                      <tr key={i}>
                        {cols.map((c) => (
                          <td key={c} dir="auto">
                            {c === "status" ? <span className={`app-pill is-${row[c]}`}>{String(row[c])}</span> : String(row[c])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </details>
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
