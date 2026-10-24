// Garden planner page: the household's water decides what can grow. A local model designs the garden from the
// household's wishes and code checks every month's water and the space; the built-in garden shows until then.
import { useEffect, useId, useRef, useState } from "react";
import { Button, Notice, SafetyBadge, months, num, type Lang } from "@brand";
import { getGarden, type GardenResponse } from "./api";
import { LinkButton, NumberField, Warnings } from "./components";
import { GARDEN } from "./gardencopy";
import { ArrowIcon } from "./icons";
import { useStored, type Store } from "./store";
import { SHELL } from "./v5copy";

const isCloud = (m: string) => m.startsWith("openrouter:");

function useGarden(s: Store) {
  const [areaRaw, setArea] = useStored("rc.garden.m2", "40");
  const [wishes, setWishes] = useStored("rc.garden.wishes", "");
  const [base, setBase] = useState<GardenResponse>();
  const [designed, setDesigned] = useState<{ key: string; res: GardenResponse }>();
  const [working, setWorking] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const ctl = useRef<AbortController>();

  const [lo, hi] = s.options?.garden.garden_m2 ?? [1, 1000];
  const typed = parseFloat(areaRaw);
  const m2 = Number.isFinite(typed) ? Math.min(hi, Math.max(lo, typed)) : lo;
  const adjusted = areaRaw.trim() !== "" && m2 !== typed;
  // key: everything that changes the garden's water or space. Wishes only matter when the model designs.
  const key = s.planKey ? `${s.planKey}|${m2}` : "";

  useEffect(() => {
    if (!key) return;
    const c = new AbortController();
    const timer = setTimeout(() => {
      getGarden({ ...s.request(), garden_m2: m2, wishes: "", model: "" }, c.signal)
        .then((g) => { setBase(g); setError(""); })
        .catch((e: Error) => { if (e.name !== "AbortError") setError(e.message); });
    }, 150);
    return () => { clearTimeout(timer); c.abort(); };
  }, [key]);

  // An AI garden belongs to the numbers it was designed for: drop it (and stop a running request) when they change.
  useEffect(() => {
    if (designed && designed.key !== key) { setDesigned(undefined); setStale(true); }
    if (working) { ctl.current?.abort(); setWorking(false); }
  }, [key]);

  const design = () => {
    if (!key || !s.ai.model) return;
    const k = key;
    const c = new AbortController();
    ctl.current = c;
    setWorking(true);
    setStale(false);
    getGarden({ ...s.request(), garden_m2: m2, wishes, model: s.ai.model }, c.signal)
      .then((g) => { setDesigned({ key: k, res: g }); setError(""); })
      .catch((e: Error) => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => { if (ctl.current === c) setWorking(false); });
  };

  const shown = designed?.key === key ? designed.res : base;
  return {
    areaRaw, setArea, adjusted, lo, hi, wishes, setWishes, shown, working, stale, error, design,
    isAI: !!designed && designed.key === key,
    cancel: () => { ctl.current?.abort(); setWorking(false); },
  };
}

export function GardenPage({ s }: { s: Store }) {
  const t = GARDEN[s.lang];
  const sh = SHELL[s.lang];
  const g = useGarden(s);
  const wishesId = useId();
  const modelId = useId();
  const models = s.options!.models;
  const shown = g.shown;
  const ai = s.ai;

  const summer = shown ? driest(shown.supply_l_week) : null;

  return (
    <section className="app-panel" aria-labelledby="h-garden">
      <div className="app-panel__head">
        <h2 id="h-garden">{t.title}</h2>
        {summer && <p>{t.waterLine(num(summer.value), months[s.lang][summer.month])}</p>}
      </div>

      <div className="app-panel__body gd-form">
        <NumberField label={t.area} unit="m²" hint={t.areaHint} value={g.areaRaw} onChange={g.setArea}
          warning={g.adjusted ? t.range(num(g.lo), num(g.hi)) : undefined} />
        <div className="app-field gd-wishes">
          <label htmlFor={wishesId}>{t.wishes}</label>
          <textarea id={wishesId} rows={3} dir="auto" maxLength={s.options!.garden.wishes_max} value={g.wishes}
            placeholder={t.wishesPlaceholder} onChange={(e) => g.setWishes(e.target.value)} aria-describedby={wishesId + "-h"} />
          <span id={wishesId + "-h"} className="app-field__hint">{t.wishesHint}</span>
        </div>
      </div>

      <div className="app-ai noprint">
        <div className="app-ai__head"><b>{t.aiTitle}</b><span>{t.aiIntro}</span></div>
        {models.length === 0 ? <Notice>{t.noModels}</Notice> : (
          <div className="app-ai__controls">
            <div className="app-field">
              <label htmlFor={modelId}>{t.model}</label>
              <select id={modelId} value={ai.model} onChange={(e) => ai.setModel(e.target.value)} disabled={g.working} dir="ltr">
                {models.map((m) => <option key={m} value={m}>{isCloud(m) ? `${m.slice(11)} (${t.cloudTag})` : m}</option>)}
              </select>
            </div>
            {g.working
              ? <Button variant="secondary" onClick={g.cancel}>{t.cancel}</Button>
              : <Button onClick={g.design} disabled={!ai.model}>{t.design}</Button>}
          </div>
        )}
        {isCloud(ai.model) && models.length > 0 && <Notice>{t.cloudNote}</Notice>}
        {g.working ? <p className="app-ai__status" role="status">{t.working(ai.model)}</p>
          : g.isAI && shown?.plan ? <p className="app-ai__status is-ok">{t.byModel(shown.model)}</p>
          : g.isAI && shown?.notice ? <Notice>{shown.notice}</Notice>
          : g.stale ? <p className="app-ai__status">{t.stale}</p>
          : shown?.notice && <p className="app-ai__status">{shown.notice}</p>}
        {g.error && <Notice><span dir="ltr">{g.error}</span></Notice>}
      </div>

      {shown && <Site g={shown} lang={s.lang} />}

      {shown && (
        <div className="gd-result">
          {g.isAI && shown.plan && <Suggestions g={shown} lang={s.lang} />}
          <figure className="gd-chart">
            <figcaption className="app-h3">{t.chartTitle}</figcaption>
            <GardenChart supply={shown.supply_l_week} demand={g.isAI ? shown.plan?.demand_l_week ?? [] : []} lang={s.lang} />
            <p className="app-note">{t.chartNote}</p>
          </figure>
          {g.isAI && <Trace g={shown} lang={s.lang} />}
          {g.isAI && shown.plan && <Care g={shown} lang={s.lang} />}
          <div className="gd-rules">
            <h3 className="app-h3">{t.rules}</h3>
            <div className="sh-warnings"><Warnings items={shown.warnings} /></div>
          </div>
        </div>
      )}

      <div className="sh-foot noprint"><LinkButton to="save">{sh.goSave}<ArrowIcon /></LinkButton></div>
    </section>
  );
}

/** Soil and air for this governorate, from SoilGrids and NASA POWER, plus the code-owned watering pattern. */
function Site({ g, lang }: { g: GardenResponse; lang: Lang }) {
  const t = GARDEN[lang];
  const { soil, humidity, watering_note } = g.site;
  const texture = t.textures[soil.texture] ?? soil.texture;
  return (
    <section className="gd-site" aria-labelledby="h-site">
      <h3 id="h-site" className="app-h3">{t.site}</h3>
      <dl>
        <div>
          <dt>{t.soil}</dt>
          <dd>{t.soilLine(texture, num(soil.ph, 1), num(soil.clay), num(soil.sand))}
            {soil.km_from_point > 0 && <small>{t.soilFar(num(soil.km_from_point))}</small>}</dd>
        </div>
        <div><dt>{t.humidity}</dt><dd>{t.humidityLine(num(humidity[6]), num(humidity[0]))}</dd></div>
        <div><dt>{t.watering}</dt><dd>{watering_note}</dd></div>
      </dl>
    </section>
  );
}

function driest(supply: number[]) {
  const month = supply.reduce((best, v, i) => (v < supply[best] ? i : best), 0);
  return { month, value: supply[month] };
}

/** The model's garden: verdict, summary and plant cards. Only rendered for a plan that passed every check. */
function Suggestions({ g, lang }: { g: GardenResponse; lang: Lang }) {
  const t = GARDEN[lang];
  const plan = g.plan!;
  const short = plan.demand_l_week.map((d, i) => (d > g.supply_l_week[i] + 1e-6 ? i : -1)).filter((i) => i >= 0);
  return (
    <>
      <div className="gd-verdict">
        <span className={`gd-pill ${short.length ? "is-short" : "is-ok"}`}>
          {short.length ? t.short(short.map((i) => months[lang][i]).join(lang === "ar" ? "، " : ", ")) : t.fits}
        </span>
        <span className="gd-area">{t.areaUsed(num(plan.area_used, 1), num(g.garden_m2))}</span>
      </div>
      <p className="gd-summary" dir="auto">{plan.summary}</p>
      <ul className="gd-plants">
        {plan.plants.map((p) => (
          <li key={p.plant_id} className={`gd-plant is-${p.kind}`}>
            <div className="gd-plant__head">
              <b>{p.name}</b>
              <span className="gd-plant__count">{t.each(num(p.count))}</span>
            </div>
            <p dir="auto">{p.reason}</p>
            <span className="gd-plant__water">{t.peak(num(p.peak_l_week))}</span>
            {p.salt_note && <span className="gd-plant__salt">{p.salt_note}</span>}
          </li>
        ))}
      </ul>
      <p className="app-note">{t.mature}</p>
    </>
  );
}

/** Every attempt the model made and why the checks accepted or rejected it. */
function Trace({ g, lang }: { g: GardenResponse; lang: Lang }) {
  const t = GARDEN[lang];
  if (g.trace.length === 0) return null;
  return (
    <div className="gd-trace">
      <h3 className="app-h3">{t.trace}</h3>
      <ol>
        {g.trace.map((a) => (
          <li key={a.attempt} className={`is-${a.outcome}`}>
            <b>{t.attempt(a.attempt)}</b>: {t.outcomes[a.outcome]}
            {a.outcome === "passed" ? ` · ${t.passedAll(g.plan?.checks.length ?? 0)}` : a.detail && <> · <span dir="ltr">{a.detail}</span></>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Care({ g, lang }: { g: GardenResponse; lang: Lang }) {
  const t = GARDEN[lang];
  const plan = g.plan!;
  const passed = plan.checks.filter((c) => c.passed).length;
  return (
    <>
      <div className="gd-care">
        <h3 className="app-h3">{t.care}</h3>
        <ol>{plan.care_steps.map((c) => <li key={c} dir="auto">{c}</li>)}</ol>
      </div>
      <div className="app-checks">
        <h3 className="app-h3">{t.checks}</h3>
        <SafetyBadge passed={passed} total={plan.checks.length} label={t.checksLabel} ofWord={t.of} />
        <ul>
          {plan.checks.map((c) => (
            <li key={c.rule} className={c.passed ? "is-pass" : "is-fail"}>
              <span aria-hidden="true">{c.passed ? "✓" : "✕"}</span> {t.checkRules[c.rule] ?? c.rule}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

const W = 420, H = 210, L = 40, R = 8, T = 10, B = 26;
const plotW = W - L - R, plotH = H - T - B;

function ticks(max: number) {
  const raw = Math.max(max, 1) / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((x) => x >= raw)!;
  return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step);
}

/** Bars: what the plants need each month. Line: what the household's water gives. Both in litres a week. */
function GardenChart({ supply, demand, lang }: { supply: number[]; demand: number[]; lang: Lang }) {
  const t = GARDEN[lang];
  const tk = ticks(Math.max(...supply, ...demand));
  const top = tk[tk.length - 1];
  const y = (v: number) => T + plotH - (v / top) * plotH;
  const band = plotW / 12;
  const x = (i: number) => L + band * i + band / 2;
  const line = supply.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <div className="rc-chart-fig">
      <div className="gd-legend" aria-hidden="true">
        {demand.length === 12 && <span><i className="gd-legend__bar" />{t.demand}</span>}
        <span><i className="gd-legend__line" />{t.supply}</span>
        <span className="gd-legend__unit">{t.perWeek}</span>
      </div>
      <svg className="rc-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.chartLabel} style={{ direction: "ltr" }}>
        {tk.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="rc-chart__grid" />
            <text x={L - 6} y={y(v) + 4} textAnchor="end">{num(v)}</text>
          </g>
        ))}
        {demand.length === 12 && demand.map((v, i) => {
          const over = v > supply[i] + 1e-6;
          return <rect key={i} x={L + band * i + 4} y={y(v)} width={band - 8} height={Math.max(0, T + plotH - y(v))}
            className={over ? "gd-bar is-short" : "gd-bar"} />;
        })}
        <path d={line} className="gd-line" />
        {supply.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={2.5} className="gd-dot" />)}
        {months[lang].map((m, i) => (
          <text key={m} x={x(i)} y={H - 8} textAnchor="middle">{lang === "en" ? m[0] : i + 1}</text>
        ))}
      </svg>
    </div>
  );
}
