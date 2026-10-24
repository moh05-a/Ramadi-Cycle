// One sticky top bar: logo, limelight nav, theme and language buttons. On phones the nav becomes a dropdown menu.
import { useEffect, useRef, useState } from "react";
import type { Lang } from "@brand";
import { DropLogo, NavCalcIcon, NavHomeIcon, NavPlanIcon } from "./icons";
import { LimelightNav } from "./limelight";
import { LangToggle, ThemeToggle } from "./toggles";
import { href, type Route } from "./router";
import type { Theme } from "./theme";
import { SHELL } from "./v5copy";

// Three destinations: the start page, the planner (the multi-step form) and how the numbers are worked out.
export type TopKey = "start" | "planner" | "calc";
const TOP: { key: TopKey; route: Route; icon: JSX.Element }[] = [
  { key: "start", route: "", icon: <NavHomeIcon /> },
  { key: "planner", route: "home", icon: <NavPlanIcon /> },
  { key: "calc", route: "calc", icon: <NavCalcIcon /> },
];

type Props = { lang: Lang; setLang: (l: Lang) => void; theme: Theme; toggleTheme: () => void; active: TopKey };

export function TopBar({ lang, setLang, theme, toggleTheme, active }: Props) {
  const sh = SHELL[lang];
  const [open, setOpen] = useState(false);
  const menuId = "sh-menu";
  const button = useRef<HTMLButtonElement>(null);

  // close the menu when the page changes, and on Escape (returning focus to the button)
  useEffect(() => setOpen(false), [active]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); button.current?.focus(); } };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const links = (cls: string) => TOP.map((t) => (
    <li key={t.key}>
      <a className={cls} href={href(t.route)} aria-current={t.key === active ? "page" : undefined} onClick={() => setOpen(false)}>
        <span>{sh.top[t.key]}</span>
      </a>
    </li>
  ));

  return (
    <header className="sh-bar">
      <div className="sh-bar__row">
        <div className="sh-bar__side">
          <a className="sh-brand" href={href("")} aria-label={`${sh.brand}, ${sh.brand2}: ${sh.homeLink}`}>
            <DropLogo />
            <span className="sh-brand__main" aria-hidden="true">{sh.brand}</span>
            <span className="sh-brand__sub" lang={lang === "ar" ? "en" : "ar"} aria-hidden="true">{sh.brand2}</span>
          </a>
        </div>

        <nav className="sh-navwrap noprint" aria-label={sh.navLabel}>
          <LimelightNav active={active}
            items={TOP.map((t) => ({ key: t.key, href: href(t.route), label: sh.top[t.key], icon: t.icon }))} />

          <div className="sh-mobile">
            <button ref={button} type="button" className="sh-mobile__btn" aria-expanded={open} aria-controls={menuId}
              aria-label={`${sh.navMenu}: ${sh.top[active]}`} onClick={() => setOpen(!open)}>
              <span>{sh.top[active]}</span>
              <span className="sh-burger" aria-hidden="true"><i /><i /></span>
            </button>
            <ul id={menuId} className="sh-mobile__menu" hidden={!open}>{links("sh-mobile__item")}</ul>
          </div>
        </nav>

        <div className="sh-bar__side sh-bar__side--end noprint">
          <ThemeToggle theme={theme} onToggle={toggleTheme} label={sh.darkMode} />
          <LangToggle lang={lang} onToggle={() => setLang(lang === "ar" ? "en" : "ar")} label={sh.langLabel} />
        </div>
      </div>
    </header>
  );
}
