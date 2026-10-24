import { useId, useRef, type ButtonHTMLAttributes, type KeyboardEvent, type ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" };

/** One primary button per screen. The label says exactly what happens. */
export function Button({ variant = "primary", className = "", type = "button", ...rest }: ButtonProps) {
  return <button type={type} className={`rc-btn rc-btn--${variant} ${className}`} {...rest} />;
}

type SelectProps = { label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void; hint?: string };

export function SelectField({ label, value, options, onChange, hint }: SelectProps) {
  const id = useId();
  return (
    <div className="rc-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} aria-describedby={hint ? id + "-h" : undefined}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {hint && <span className="rc-field__hint" id={id + "-h"}>{hint}</span>}
    </div>
  );
}

type SliderProps = { label: string; value: number; min: number; max: number; step?: number; unit: string; onChange: (v: number) => void; hint?: string };

/** Every slider shows its value and unit. Set min and max so a demo can't reach absurd numbers. */
export function SliderField({ label, value, min, max, step = 1, unit, onChange, hint }: SliderProps) {
  const id = useId();
  return (
    <div className="rc-field">
      <div className="rc-field__top">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id}>{value} {unit}</output>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} aria-valuetext={`${value} ${unit}`}
        onChange={(e) => onChange(Number(e.target.value))} aria-describedby={hint ? id + "-h" : undefined} />
      {hint && <span className="rc-field__hint" id={id + "-h"}>{hint}</span>}
    </div>
  );
}

export function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  const id = useId();
  return (
    <label className="rc-toggle" htmlFor={id}>
      <input id={id} type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

type Tab = { id: string; label: string; panel: ReactNode };

/** WAI-ARIA tabs. Arrow keys follow reading direction, so Right moves back in Arabic. */
export function Tabs({ tabs, active, onChange }: { tabs: Tab[]; active: string; onChange: (id: string) => void }) {
  const base = useId();
  const list = useRef<HTMLDivElement>(null);
  const onKey = (e: KeyboardEvent) => {
    const rtl = getComputedStyle(list.current!).direction === "rtl";
    const step = { ArrowRight: rtl ? -1 : 1, ArrowLeft: rtl ? 1 : -1 }[e.key];
    let next = tabs.findIndex((t) => t.id === active);
    if (step) next = (next + step + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    onChange(tabs[next].id);
    list.current!.querySelectorAll<HTMLButtonElement>("[role=tab]")[next].focus();
  };
  return (
    <div className="rc-tabs">
      <div className="rc-tabs__list" role="tablist" ref={list} onKeyDown={onKey}>
        {tabs.map((t) => (
          <button key={t.id} type="button" role="tab" id={`${base}-${t.id}`} aria-controls={`${base}-${t.id}-p`}
            aria-selected={t.id === active} tabIndex={t.id === active ? 0 : -1} onClick={() => onChange(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      {tabs.map((t) => (
        <div key={t.id} role="tabpanel" id={`${base}-${t.id}-p`} aria-labelledby={`${base}-${t.id}`} hidden={t.id !== active} tabIndex={0}>
          {t.panel}
        </div>
      ))}
    </div>
  );
}
