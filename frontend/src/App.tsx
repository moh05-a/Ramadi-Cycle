// v5 design: four pages (home, savings, build plan, how we calculated). All numbers and plan text come from the API.
import { useEffect, useState } from "react";
import { Button, Notice, Tabs, num } from "@brand";
import { COPY } from "./copy";
import { Assumptions, Method, detailLines } from "./calc";
import { AIBox, PlanPrompt, Charts, Community, GovField, LinkButton, NumberField, SafetyChecks, Sareef, Steps, Warnings } from "./components";
import { GardenPage } from "./garden";
import { Hero, useOverHero } from "./hero";
import { Wizard, isStep } from "./wizard";
import { ArrowIcon, DownloadIcon, PrintIcon } from "./icons";
import { TopBar } from "./topbar";
import { useRoute, type Route } from "./router";
import { FIELDS, useRamadi, type Store } from "./store";
import { useTheme } from "./theme";
import { SHELL, type Page } from "./v5copy";

const PAGE_OF: Record<Route, Page> = {
  "": "home", home: "home", garden: "garden", save: "save", dashboard: "save", plan: "plan", calc: "calc", method: "calc", data: "calc",
};

export function App() {
  const s = useRamadi();
  const route = useRoute();
  const { theme, toggle } = useTheme();
  const page = PAGE_OF[route];
  const landing = route === ""; // the hero alone; "Check my home" goes to the form at #/home
  const overHero = useOverHero(landing);
  const t = COPY[s.lang];
  const sh = SHELL[s.lang];

  useEffect(() => { document.title = "Suqya | سُقيا"; }, []);

  // A dead API looks like a failed fetch. Any other error is a real answer from the API, so show it as is.
  const unreachable = /failed to fetch|networkerror|load failed/i.test(s.error);

  return (
    <div className={`rc-root sh${landing ? " sh--landing" : ""}${overHero ? " sh--over-hero" : ""}`} dir={s.lang === "ar" ? "rtl" : "ltr"} lang={s.lang}>
      <a className="sh-skip" href="#main">{sh.skip}</a>

      <TopBar lang={s.lang} setLang={s.setLang} theme={theme} toggleTheme={toggle}
        active={landing ? "start" : isStep(page) ? "planner" : "calc"} />

      <main id="main">
        {landing ? <Hero lang={s.lang} /> : <>
        <h1 className="sh-sr" tabIndex={-1}>{sh.nav[page]}</h1>

        <div className="sh-col">
          {s.error && (
            <div className="app-error noprint" role="alert">
              <Notice>
                {unreachable && <>{sh.unreachable} <code dir="ltr">python api.py</code></>}
                <span className={unreachable ? "app-error__detail" : ""} dir="ltr">{unreachable ? `(${s.error})` : s.error}</span>
              </Notice>
              <Button variant="secondary" onClick={s.retry}>{t.retry}</Button>
            </div>
          )}

          {(() => {
            const body = page === "home" ? <HomePage s={s} />
              : s.data && s.options ? <Results page={page} s={s} />
              : !s.error && <p className="app-loading" aria-live="polite">{t.loading}</p>;
            return isStep(page) ? <Wizard step={page} lang={s.lang}>{body}</Wizard> : body;
          })()}

          {page !== "home" && s.data && <p className="app-disclaimer">{s.data.disclaimer}</p>}
        </div>
        </>}
      </main>
    </div>
  );
}


function HomePage({ s }: { s: Store }) {
  const t = COPY[s.lang];
  const o = s.options;
  return (
    <section className="app-panel" aria-labelledby="h-home">
      <div className="app-panel__head"><h2 id="h-home">{t.step1}</h2></div>
      <div className="app-panel__body app-form__body">
        <GovField label={t.gov} value={s.gov} onChange={s.setGov} options={o?.governorates ?? []} names={t.govNames} />
        {FIELDS.map((k) => (
          <NumberField key={k} {...t.fields[k]} value={s.form[k] ?? ""} onChange={(v) => s.setForm(k, v)}
            warning={s.fields?.[k].adjusted && o ? t.range(...o.limits[k]) : undefined} />
        ))}
        <fieldset className="app-choice">
          <legend>{t.year}</legend>
          <div className="app-choice__row">
            {(o?.years ?? []).map((y) => (
              <label key={y} className="app-choice__opt">
                <input type="radio" name="year" value={y} checked={s.year === y} onChange={() => s.setYear(y)} />
                <span>{t.years[y]}</span>
              </label>
            ))}
          </div>
          <span className="app-field__hint">{t.yearHint}</span>
        </fieldset>
        <fieldset className="app-budget">
          <legend>{t.budget}</legend>
          {(o?.budgets ?? []).map((b) => (
            <label key={b} className="app-budget__opt">
              <input type="radio" name="budget" value={b} checked={s.budget === b} onChange={() => s.setBudget(b)} />
              <span className="app-budget__text">
                <b>{t.budgets[b][0]}</b>
                <span>{t.budgets[b][1].replace("{c}", s.data ? num(s.data.budget_costs[b]) : "…")}</span>
              </span>
            </label>
          ))}
        </fieldset>
      </div>
    </section>
  );
}

function Results({ page, s }: { page: Page; s: Store }) {
  if (page === "garden") return <GardenPage s={s} />;
  if (page === "save") return <SavePage s={s} />;
  if (page === "plan") return <PlanPage s={s} />;
  return <CalcPage s={s} />;
}

function SavePage({ s }: { s: Store }) {
  const t = COPY[s.lang];
  const { profile, result: res } = s.data!;
  const imp = s.data!.impact; // plan-independent: payback uses the standard parts list
  const payback = imp.payback_months;
  const cells = [
    { key: "trips", value: num(imp.trips, 1), unit: t.results.trips[1], label: t.results.trips[0], cls: "" },
    { key: "water", value: num(res.water, 1), unit: t.results.water[1], label: t.results.water[0], cls: "is-water" },
    { key: "pay", value: payback == null ? t.none : num(payback), unit: payback == null ? "" : t.results.pay[1], label: t.results.pay[0], cls: "" },
  ];
  return (
    <section className="app-panel" aria-labelledby="h-save">
      <div className="app-panel__head is-dark">
        <h2 id="h-save">{t.step2}</h2>
        <span>{t.line(t.govNames[profile.governorate] ?? profile.governorate, num(profile.rain_mm), num(profile.roof_m2), num(profile.people))}</span>
      </div>
      <div className="app-headline">
        <span className="app-headline__label">{t.results.jod[0]}</span>
        <span className="app-headline__row">
          <span className="app-headline__value">{num(imp.jod)}</span>
          <span className="app-headline__unit">{t.results.jod[1]}</span>
        </span>
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
      <div className="app-panel__foot">{t.estimateNote(t.years[s.year])}</div>
    </section>
  );
}

function PlanPage({ s }: { s: Store }) {
  const t = COPY[s.lang];
  const sh = SHELL[s.lang];
  const [tab, setTab] = useState("steps");
  if (!s.shown) return <PlanPrompt s={s} />;
  const shown = s.shown;
  const { plan, markdown } = shown;
  const data = s.data!;

  const download = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([markdown], { type: "text/markdown" }));
    a.download = `suqya-plan-${plan.language}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const panels = {
    steps: (
      <div className="app-steps-grid">
        <Steps title={t.rain} steps={plan.rainwater_steps} tone="rain" />
        <Steps title={t.grey} steps={plan.greywater_steps} tone="grey" />
      </div>
    ),
    buy: (
      <div>
        <ul className="sh-bom">
          {plan.bom.map((row, i) => (
            <li key={row.item + i}>
              <span className="sh-bom__item">
                {row.item}
                {plan.source === "model" && row.why && <small>{row.why}</small>}
              </span>
              <span className="sh-bom__qty">× {num(row.qty)}</span>
              <span className="sh-bom__price">{num(row.total_jod)} {t.jod}</span>
            </li>
          ))}
        </ul>
        <div className="sh-bomfoot">
          <span className="app-note">{t.pricesNote}</span>
          <b>{t.total}: {num(plan.cost)} {t.jod}</b>
        </div>
        {Math.abs(plan.cost - shown.payback_cost) > 0.5 && <p className="app-note">{t.paybackNote(num(shown.payback_cost))}</p>}
      </div>
    ),
    plants: plan.plants.length ? (
      <ul className="app-plants">
        {plan.plants.map((p) => <li key={p.plant_id}><span><b>{p.name}</b>: {p.reason}</span></li>)}
      </ul>
    ) : (
      <div className="app-notrees">
        <p>{sh.noTrees}</p>
        <LinkButton to="garden" variant="secondary">{sh.toGarden}<ArrowIcon /></LinkButton>
      </div>
    ),
  };

  return (
    <section className="app-panel" aria-labelledby="h-plan">
      <div className="app-panel__head">
        <h2 id="h-plan">{t.step3}</h2>
        <p>{plan.summary}</p>
      </div>

      <AIBox ai={s.ai} plan={plan} models={s.options!.models} lang={s.lang} />

      <div className="sh-tabs">
        <Tabs active={tab} onChange={setTab}
          tabs={(["steps", "buy", "plants"] as const).map((id) => ({ id, label: sh.tabs[id], panel: panels[id] }))} />
      </div>

      <div className="app-safety">
        <h3 className="app-h3 app-safety__title">{t.safety}</h3>
        <SafetyChecks plan={plan} lang={s.lang} collapsed />
        <div className="sh-warnings"><Warnings items={data.warnings} /></div>
      </div>

      <div className="app-actions noprint">
        <Button onClick={() => window.print()}><PrintIcon />{t.print}</Button>
        <Button variant="secondary" onClick={download}><DownloadIcon />{t.download}</Button>
      </div>
    </section>
  );
}

function CalcPage({ s }: { s: Store }) {
  const t = COPY[s.lang];
  const data = s.data!;
  const lines = detailLines(data, data.impact.co2, s.lang);
  return (
    <>
      <section className="app-panel" aria-labelledby="h-calc">
        <div className="app-panel__head"><h2 id="h-calc">{t.details}</h2></div>
        <ul className="sh-lines">{lines.map((d) => <li key={d}>{d}</li>)}</ul>
      </section>

      <section className="sh-stack" aria-labelledby="h-impact">
        <h2 id="h-impact" className="sh-section-title">{t.impact}</h2>
        <Charts data={data} lang={s.lang} />
        <Sareef data={data} lang={s.lang} />
        <Community s={s} />
      </section>

      <Method data={data} options={s.options!} lang={s.lang} model={s.ai.isAI ? s.ai.model : ""} />
      <Assumptions options={s.options!} lang={s.lang} />
    </>
  );
}
