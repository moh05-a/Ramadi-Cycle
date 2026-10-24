// Detail sections of the "How we calculated" page: method and data tables. Everything comes from /api/options.
import { Warning, num, type Lang } from "@brand";
import type { Options, PlanResponse } from "./api";
import { COPY } from "./copy";
import { DataTable, TABLE_ORDER } from "./components";

const isCloud = (m: string) => m.startsWith("openrouter:");

export function Method({ data, options, lang, model }: { data: PlanResponse; options: Options; lang: Lang; model: string }) {
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

export function Assumptions({ options, lang }: { options: Options; lang: Lang }) {
  const t = COPY[lang];
  const rows = options.tables.assumptions;
  const verified = rows.filter((r) => r.status === "verified" || r.status === "sourced").length;
  return (
    <details className="app-panel app-details app-method noprint">
      <summary>{t.data}</summary>
      <div className="app-method__body">
        <p className="app-note">{t.dataIntro(verified, rows.length)}</p>
        {TABLE_ORDER.map((key) => (
          <div key={key}>
            <h3 className="app-h3">{t.tables[key]}</h3>
            <DataTable rows={options.tables[key]} label={t.tables[key]} columns={t.columns} />
          </div>
        ))}
      </div>
    </details>
  );
}

/** The short worked lines at the top of the page. */
export function detailLines(data: PlanResponse, impactCo2: number, lang: Lang) {
  const { result: res, assumptions: a } = data;
  return COPY[lang].detailLines({
    rainUsed: num(res.rain_used, 1), grey: num(res.greywater, 1), co2: num(impactCo2),
    tankerVolume: num(a.tanker_volume), tankerPrice: num(a.tanker_price), litres: num(a.nonpotable_litres_per_person_day),
  });
}
