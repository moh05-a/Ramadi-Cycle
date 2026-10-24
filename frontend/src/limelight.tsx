// "Limelight" navigation: a bar of icon + label links with a light that slides over the current page and casts a
// soft cone onto it. The current page comes from the route (not internal state), and items are real links.
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

export type LimeItem = { key: string; href: string; label: string; icon: ReactNode };

export function LimelightNav({ items, active }: { items: LimeItem[]; active: string | null }) {
  const nav = useRef<HTMLUListElement>(null);
  const light = useRef<HTMLSpanElement>(null);
  const [ready, setReady] = useState(false); // no slide on first paint, only between pages

  useLayoutEffect(() => {
    const place = () => {
      const el = nav.current?.querySelector<HTMLElement>(`[data-key="${active}"]`);
      if (!light.current) return;
      if (!el) { light.current.style.opacity = "0"; return; }
      light.current.style.opacity = "1";
      light.current.style.left = `${el.offsetLeft + el.offsetWidth / 2 - light.current.offsetWidth / 2}px`;
    };
    place();
    const id = window.setTimeout(() => setReady(true), 50);
    // labels change width with the language and once fonts load, so re-place on any size change
    const ro = new ResizeObserver(place);
    if (nav.current) ro.observe(nav.current);
    return () => { window.clearTimeout(id); ro.disconnect(); };
  }, [active, items.map((i) => i.label).join("|")]); // re-place only when the page or the labels change

  return (
    <ul ref={nav} className={`lime${ready ? " is-ready" : ""}`}>
      {items.map((it) => (
        <li key={it.key}>
          <a className="lime__item" data-key={it.key} href={it.href} aria-current={it.key === active ? "page" : undefined}>
            <span className="lime__icon">{it.icon}</span>
            <span className="lime__label">{it.label}</span>
          </a>
        </li>
      ))}
      <li className="lime__light-wrap" aria-hidden="true"><span ref={light} className="lime__light" /></li>
    </ul>
  );
}
