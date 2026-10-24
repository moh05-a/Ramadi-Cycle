import type { ReactNode } from "react";

/** Status is never colour alone: icon + words. */
export function SafetyBadge({ passed, total, label, ofWord = "of" }: { passed: number; total: number; label: string; ofWord?: string }) {
  const ok = passed === total;
  return (
    <span className={`rc-badge ${ok ? "is-pass" : "is-fail"}`} role="status">
      <svg viewBox="0 0 14 14" width="14" height="14" aria-hidden="true">
        {ok
          ? <path d="M2 7.5l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />
          : <path d="M3 3l8 8M11 3l-8 8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />}
      </svg>
      {label}: {passed} {ofWord} {total}
    </span>
  );
}

/** Fixed safety rule: rust triangle + real text, so it never depends on colour or images. */
export function Warning({ children }: { children: ReactNode }) {
  return (
    <p className="rc-warning">
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
        <path d="M8 1.5 15 14.5H1z" fill="currentColor" />
        <path d="M8 6v4" stroke="var(--rc-bg)" strokeWidth="1.6" />
        <rect x="7.2" y="11.2" width="1.6" height="1.6" fill="var(--rc-bg)" />
      </svg>
      <span>{children}</span>
    </p>
  );
}

/** Neutral information, e.g. the template fallback. Not danger, so no rust. */
export function Notice({ children }: { children: ReactNode }) {
  return <div className="rc-notice" role="note">{children}</div>;
}
