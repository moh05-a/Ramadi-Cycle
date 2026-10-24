import type { ReactNode } from "react";
import { num } from "../i18n";

type MetricProps = { label: string; value: number; decimals?: number; unit: string; delta?: { value: number; good: boolean } };

/** Value and unit always together. m³ to one decimal, JOD and kg whole. */
export function Metric({ label, value, decimals = 0, unit, delta }: MetricProps) {
  return (
    <div className="rc-metric">
      <span className="rc-metric__label">{label}</span>
      <span className="rc-metric__value">{num(value, decimals)}<small>{unit}</small></span>
      {delta && (
        <span className={`rc-metric__delta ${delta.good ? "is-good" : "is-bad"}`}>
          <span aria-hidden="true">{delta.value < 0 ? "↓" : "↑"}</span> {num(Math.abs(delta.value), decimals)}
        </span>
      )}
    </div>
  );
}

export function MetricRow({ children }: { children: ReactNode }) {
  return <div className="rc-metric-row">{children}</div>;
}

export type BomRow = { item: string; qty: number; unit: string; unitJod: number };
type BomLabels = { item: string; qty: string; each: string; total: string; sum: string };

export function BomTable({ rows, labels, caption }: { rows: BomRow[]; labels: BomLabels; caption?: string }) {
  const sum = rows.reduce((s, r) => s + r.qty * r.unitJod, 0);
  return (
    <div className="rc-table-wrap" tabIndex={0} role="region" aria-label={caption ?? labels.item}>
      <table className="rc-table">
        {caption && <caption>{caption}</caption>}
        <thead>
          <tr><th scope="col">{labels.item}</th><th scope="col">{labels.qty}</th><th scope="col">{labels.each}</th><th scope="col">{labels.total}</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.item}><td>{r.item}</td><td>{num(r.qty)} {r.unit}</td><td>{num(r.unitJod)}</td><td>{num(r.qty * r.unitJod)}</td></tr>
          ))}
        </tbody>
        <tfoot>
          <tr><th scope="row" colSpan={3}>{labels.sum}</th><td>{num(sum)}</td></tr>
        </tfoot>
      </table>
    </div>
  );
}
