// Pieces shared by several pages. Numbers and plan text always come from the API response.
import { useId, useState, type ReactNode } from "react";
import { Button, MonthlyBars, Notice, SafetyBadge, TankLine, Warning, num, type Lang } from "@brand";
import type { Options, PlanBlock, PlanResponse, TableKey } from "./api";
import { COPY, PAGES } from "./copy";
import { href, type Route } from "./router";
import type { AI, Store } from "./store";

export function GovField({ label, value, onChange, options, names }: {
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

export function NumberField({ label, unit, hint, warning, value, onChange }: NumberFieldProps) {
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

/** Link styled as a button. Navigation stays a real link so it can be opened in a new tab. */
export function LinkButton({ to, children, variant = "primary" }: { to: Route; children: ReactNode; variant?: "primary" | "secondary" }) {
  return <a className={`rc-btn rc-btn--${variant} app-linkbtn`} href={href(to)}>{children}</a>;
}

/** Three-step workflow indicator: home → savings → plan. */
export function Stepper({ lang, active }: { lang: Lang; active: 0 | 1 | 2 }) {
  const p = PAGES[lang];
  const to: Route[] = ["home", "dashboard", "plan"];
  return (
    <nav className="app-stepper noprint" aria-label={p.stepLabel}>
      <ol>
        {p.steps.map((label, i) => (
          <li key={label} className={i === active ? "is-active" : i < active ? "is-done" : ""}>
            <a href={href(to[i])} aria-current={i === active ? "step" : undefined}>
              <span className="app-stepper__n" aria-hidden="true">{i + 1}</span>
              <span><span className="app-sr">{p.stepLabel} {i + 1}: </span>{label}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function PageHead({ title, sub, children }: { title: string; sub?: ReactNode; children?: ReactNode }) {
  return (
    <div className="app-pagehead">
      <div className="app-pagehead__text">
        <h1 tabIndex={-1}>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      {children}
    </div>
  );
}

export function Kpis({ s }: { s: Store }) {
  const t = COPY[s.lang];
  const { data, shown } = s;
  if (!data || !shown) return null;
  const imp = shown.impact;
  const payback = imp.payback_months;
  const cells = [
    { key: "trips", value: num(imp.trips, 1), unit: t.results.trips[1], label: t.results.trips[0], cls: "" },
    { key: "water", value: num(data.result.water, 1), unit: t.results.water[1], label: t.results.water[0], cls: "is-water" },
    { key: "pay", value: payback == null ? t.none : num(payback), unit: payback == null ? "" : t.results.pay[1], label: t.results.pay[0], cls: "" },
    { key: "co2", value: num(imp.co2), unit: t.sareefRows.co2[1], label: PAGES[s.lang].dash.co2, cls: "" },
  ];
  return (
    <section className="app-panel app-kpis" aria-label={PAGES[s.lang].dash.title}>
      <div className="app-headline">
        <span className="app-headline__label">{t.results.jod[0]}</span>
        <span className="app-headline__row">
          <span className="app-headline__value">{num(imp.jod)}</span>
          <span className="app-headline__unit">{t.results.jod[1]}</span>
        </span>
        <span className="app-note">{t.estimateNote(t.years[s.year])}</span>
      </div>
      <div className="app-secondary">
        {cells.map((c) => (
          <div key={c.key} className="app-secondary__cell">
            <span className="app-secondary__label">{c.label}</span>
            <span className="app-secondary__row">
              <span className={`app-secondary__value ${c.cls}`}>{c.value}</span>
              <span className="app-secondary__unit">{c.unit}</span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Charts({ data, lang }: { data: PlanResponse; lang: Lang }) {
  const t = COPY[lang];
  const res = data.result;
  return (
    <>
      <figure className="app-panel app-card app-chart">
        <figcaption className="app-h3">{t.tankChart}</figcaption>
        <TankLine lang={lang} level={data.balance.map((m) => m.level)} capacity={data.profile.capacity_m3} label={t.tankChart} legend={t.tankLegend} />
        <p className="app-note">{t.chartSummary(num(res.dry_months), num(res.overflow, 1), num(res.rain_used, 1), num(res.potential, 1))}</p>
      </figure>
      <figure className="app-panel app-card app-chart">
        <figcaption className="app-h3">{t.demandChart}</figcaption>
        <MonthlyBars lang={lang} label={t.demandChart} series={[
          { label: t.fromRain, values: data.balance.map((m) => m.met), color: "cistern" },
          { label: t.bought, values: data.balance.map((m) => m.shortfall), color: "bought" },
        ]} />
      </figure>
    </>
  );
}

export function Sareef({ data, lang }: { data: PlanResponse; lang: Lang }) {
  const t = COPY[lang];
  const [view, setView] = useState<"today" | "with">("with");
  const { sareef } = data;
  const now = view === "with" ? sareef.now : sareef.before;
  const rows = [{ key: "trips" as const, d: 1 }, { key: "jod" as const, d: 0 }, { key: "co2" as const, d: 0 }];
  return (
    <section className="app-panel app-card app-sareef" aria-labelledby="h-sareef">
      <h2 id="h-sareef" className="app-h3">{t.sareef} <span lang="ar">· صهريج</span></h2>
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
    </section>
  );
}

export function Community({ s }: { s: Store }) {
  const t = COPY[s.lang];
  const id = useId();
  const com = s.data!.community;
  return (
    <section className="app-panel app-card app-community" aria-labelledby="h-community">
      <h2 id="h-community" className="app-h3">{t.community}</h2>
      <label htmlFor={id} className="app-community__label">{t.homes} <output htmlFor={id}>{num(s.homes)}</output></label>
      <input id={id} type="range" min={1} max={s.options!.community_max} step={1} value={s.homes} onChange={(e) => s.setHomes(Number(e.target.value))} />
      <p>{t.communityLine(num(com.homes), num(com.water), num(com.trips), num(com.co2_t, 1))}</p>
    </section>
  );
}

export function AIBox({ ai, plan, models, lang }: { ai: AI; plan: PlanBlock["plan"]; models: string[]; lang: Lang }) {
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
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          {ai.generating
            ? <Button variant="secondary" onClick={ai.cancel}>{t.aiCancel}</Button>
            : <Button onClick={ai.write} disabled={!ai.model}>{t.aiButton}</Button>}
          {ai.isAI && !ai.generating && <Button variant="secondary" onClick={ai.reset}>{t.useTemplate}</Button>}
        </div>
      )}
      {ai.generating ? <p className="app-ai__status" role="status">{t.aiWorking(ai.model)}</p> : status}
    </div>
  );
}

export function SafetyChecks({ plan, lang }: { plan: PlanBlock["plan"]; lang: Lang }) {
  const t = COPY[lang];
  return (
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
  );
}

export function Steps({ title, steps, tone }: { title: string; steps: string[]; tone: "rain" | "grey" }) {
  return (
    <div className={`app-steps is-${tone}`}>
      <h3 className="app-h3">{title}</h3>
      <ol>{steps.map((s) => <li key={s}>{s}</li>)}</ol>
    </div>
  );
}

export function Warnings({ items }: { items: string[] }) {
  return <>{items.map((w) => <Warning key={w}>{w}</Warning>)}</>;
}

export function DataTable({ rows, label, columns }: { rows: Record<string, string | number | boolean>[]; label: string; columns: Record<string, string> }) {
  const cols = Object.keys(rows[0] ?? {});
  return (
    <div className="rc-table-wrap" tabIndex={0} role="region" aria-label={label}>
      <table className="rc-table app-data">
        <thead><tr>{cols.map((c) => <th key={c} scope="col">{columns[c] ?? c.replace(/_/g, " ")}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
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
  );
}

export const TABLE_ORDER: TableKey[] = ["assumptions", "rainfall", "monthly_share", "catalog", "plants"];
