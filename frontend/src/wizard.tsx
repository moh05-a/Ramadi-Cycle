// The planner as one multi-step form: progress dots and bar, the step's content sliding in, Back/Next, and
// "Step 2 of 4". Each step keeps its own address (#/home, #/garden, ...) so back, reload and sharing still work.
import { useEffect, useRef, type ReactNode } from "react";
import type { Lang } from "@brand";
import { ArrowIcon } from "./icons";
import { href } from "./router";
import { useStored } from "./store";
import { SHELL, type Page } from "./v5copy";

export const STEPS = ["home", "garden", "save", "plan"] as const;
export type Step = (typeof STEPS)[number];
export const isStep = (p: Page): p is Step => (STEPS as readonly string[]).includes(p);

export function Wizard({ step, lang, children }: { step: Step; lang: Lang; children: ReactNode }) {
  const sh = SHELL[lang];
  const i = STEPS.indexOf(step);
  const last = STEPS.length - 1;
  // slide direction: forward when moving to a later step, backward otherwise
  const prev = useRef(i);
  const dir = i >= prev.current ? "fwd" : "back";
  useEffect(() => { prev.current = i; }, [i]);
  // dots link only to steps already reached, like a real form; remembered across reloads
  const [reached, setReached] = useStored("rc.reached", 0);
  useEffect(() => { if (i > reached) setReached(i); }, [i]);
  const nextLabel = [sh.goGarden, sh.goSave, sh.goPlan][i];

  return (
    <div className="wz">
      <nav className="wz-progress noprint" aria-label={sh.stepsLabel}>
        <ol>
          {STEPS.map((p, n) => {
            const cls = n < i ? "is-done" : n === i ? "is-current" : "";
            const inner = <><span className="wz-dot" aria-hidden="true" /><span className="wz-label">{sh.nav[p]}</span></>;
            return (
              <li key={p} className={cls}>
                {n <= reached
                  ? <a href={href(p)} aria-current={n === i ? "step" : undefined}>{inner}</a>
                  : <span className="wz-locked" aria-disabled="true">{inner}</span>}
              </li>
            );
          })}
        </ol>
        <div className="wz-bar" aria-hidden="true"><span style={{ inlineSize: `${(i / last) * 100}%` }} /></div>
      </nav>

      <div key={step} className={`wz-body is-${dir}`}>{children}</div>

      <div className="wz-foot noprint">
        {i > 0
          ? <a className="rc-btn rc-btn--secondary wz-back" href={href(STEPS[i - 1])}><ArrowIcon />{sh.back}</a>
          : <span />}
        {i < last
          ? <a className="rc-btn rc-btn--primary wz-next" href={href(STEPS[i + 1])}>{nextLabel}<ArrowIcon /></a>
          : <a className="rc-btn rc-btn--secondary wz-next" href={href("calc")}>{sh.goCalc}<ArrowIcon /></a>}
      </div>
      <p className="wz-count" aria-live="polite">{sh.stepOf(i + 1, STEPS.length, sh.nav[step])}</p>
    </div>
  );
}
