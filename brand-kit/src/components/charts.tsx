import { months, num, type Lang } from "../i18n";

/** Up to 6 round ticks from 0 that cover max. */
export function niceTicks(max: number): number[] {
  if (!(max > 0)) return [0, 1];
  const raw = max / 5;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)!;
  const top = Math.ceil(max / step - 1e-9) * step;
  return Array.from({ length: Math.round(top / step) + 1 }, (_, i) => +(i * step).toFixed(10));
}

const W = 420, H = 200, L = 34, R = 8, T = 8, B = 26;
const plotW = W - L - R, plotH = H - T - B;

function Frame({ ticks, lang, children, label }: { ticks: number[]; lang: Lang; children: React.ReactNode; label: string }) {
  const top = ticks[ticks.length - 1];
  const y = (v: number) => T + plotH - (v / top) * plotH;
  const band = plotW / 12;
  return (
    // Time runs left to right in both languages, so the chart stays LTR inside an RTL page.
    <svg className="rc-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} style={{ direction: "ltr" }}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="rc-chart__grid" />
          <text x={L - 6} y={y(t) + 4} textAnchor="end">{num(t, t % 1 ? 1 : 0)}</text>
        </g>
      ))}
      {months[lang].map((m, i) => (
        <text key={m} x={L + band * i + band / 2} y={H - 8} textAnchor="middle">{lang === "en" ? m[0] : i + 1}</text>
      ))}
      {children}
    </svg>
  );
}

export type BarSeries = { label: string; values: number[]; color: "cistern" | "olive" | "bought" };

/** Stacked monthly bars. Series stack bottom-up in the order given. */
export function MonthlyBars({ series, lang, label }: { series: BarSeries[]; lang: Lang; label: string }) {
  const totals = months.en.map((_, i) => series.reduce((s, x) => s + (x.values[i] ?? 0), 0));
  const ticks = niceTicks(Math.max(...totals));
  const top = ticks[ticks.length - 1];
  const band = plotW / 12, bw = band - 6;
  return (
    <figure className="rc-chart-fig">
      <Legend items={series.map((s) => ({ label: s.label, swatch: `var(--rc-${s.color})` }))} />
      <Frame ticks={ticks} lang={lang} label={label}>
        {months.en.map((_, i) => {
          let base = T + plotH;
          return series.map((s) => {
            const h = ((s.values[i] ?? 0) / top) * plotH;
            base -= h;
            return h > 0 ? <rect key={s.label + i} x={L + band * i + 3} y={base} width={bw} height={h} fill={`var(--rc-${s.color})`} /> : null;
          });
        })}
      </Frame>
    </figure>
  );
}

/** Harvest tank level with capacity as a dashed rule. */
export function TankLine({ level, capacity, lang, label, legend }: { level: number[]; capacity: number; lang: Lang; label: string; legend: [string, string] }) {
  const ticks = niceTicks(Math.max(capacity, ...level) * 1.15);
  const top = ticks[ticks.length - 1];
  const band = plotW / 12;
  const x = (i: number) => L + band * i + band / 2;
  const y = (v: number) => T + plotH - (v / top) * plotH;
  return (
    <figure className="rc-chart-fig">
      <Legend items={[{ label: legend[0], swatch: "var(--rc-cistern)" }, { label: legend[1], swatch: "dashed" }]} />
      <Frame ticks={ticks} lang={lang} label={label}>
        <line x1={L} x2={W - R} y1={y(capacity)} y2={y(capacity)} className="rc-chart__cap" />
        <polyline fill="none" stroke="var(--rc-cistern)" strokeWidth="2" points={level.map((v, i) => `${x(i)},${y(v)}`).join(" ")} />
        {level.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r="3" fill="var(--rc-cistern)" />)}
      </Frame>
    </figure>
  );
}

function Legend({ items }: { items: { label: string; swatch: string }[] }) {
  return (
    <figcaption className="rc-legend">
      {items.map((it) => (
        <span key={it.label}>
          <i aria-hidden="true" className={it.swatch === "dashed" ? "is-dashed" : ""} style={it.swatch === "dashed" ? undefined : { background: it.swatch }} />
          {it.label}
        </span>
      ))}
    </figcaption>
  );
}
