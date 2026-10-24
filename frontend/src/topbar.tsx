// One sticky top bar: logo, pill nav, theme switch, language switch. On phones the pill becomes a dropdown menu.
import { useEffect, useRef, useState } from "react";
import type { Lang } from "@brand";
import { DropLogo } from "./icons";
import { href, type Route } from "./router";
import type { Theme } from "./theme";
import { PAGES_ORDER, SHELL, type Page } from "./v5copy";

const ROUTE_OF: Record<Page, Route> = { home: "home", garden: "garden", save: "save", plan: "plan", calc: "calc" };
const RAY_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315];

type Props = { lang: Lang; setLang: (l: Lang) => void; theme: Theme; toggleTheme: () => void; page: Page };

export function TopBar({ lang, setLang, theme, toggleTheme, page }: Props) {
  const sh = SHELL[lang];
  const [open, setOpen] = useState(false);
  const menuId = "sh-menu";
  const button = useRef<HTMLButtonElement>(null);

  // close the menu when the page changes, and on Escape (returning focus to the button)
  useEffect(() => setOpen(false), [page]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); button.current?.focus(); } };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const links = (cls: string) => PAGES_ORDER.map((p) => (
    <li key={p}>
      <a className={cls} href={href(ROUTE_OF[p])} aria-current={p === page ? "page" : undefined} onClick={() => setOpen(false)}>
        <span>{sh.nav[p]}</span>
      </a>
    </li>
  ));

  return (
    <header className="sh-bar">
      <div className="sh-bar__row">
        <div className="sh-bar__side">
          <div className="sh-brand">
            <DropLogo />
            <span className="sh-brand__main">{sh.brand}</span>
            <span className="sh-brand__sub" lang={lang === "ar" ? "en" : "ar"}>{sh.brand2}</span>
          </div>
        </div>

        <nav className="sh-navwrap noprint" aria-label={sh.navLabel}>
          <ul className="sh-pill">{links("sh-pill__item")}</ul>

          <div className="sh-mobile">
            <button ref={button} type="button" className="sh-mobile__btn" aria-expanded={open} aria-controls={menuId}
              aria-label={`${sh.navMenu}: ${sh.nav[page]}`} onClick={() => setOpen(!open)}>
              <span>{sh.nav[page]}</span>
              <span className="sh-burger" aria-hidden="true"><i /><i /></span>
            </button>
            <ul id={menuId} className="sh-mobile__menu" hidden={!open}>{links("sh-mobile__item")}</ul>
          </div>
        </nav>

        <div className="sh-bar__side sh-bar__side--end noprint">
          <button type="button" role="switch" className="sh-sw sh-sw--theme" aria-checked={theme === "dark"} aria-label={sh.darkMode} onClick={toggleTheme}>
            <span className="sh-sw__track" />
            <span className="sh-sw__knob" />
            <span className="sh-sun" aria-hidden="true">
              <span className="sh-sun__disc" />
              {RAY_ANGLES.map((a) => <span key={a} className="sh-ray" style={{ "--a": `${a}deg` } as React.CSSProperties} />)}
            </span>
          </button>
          <button type="button" role="switch" className="sh-sw sh-sw--lang" aria-checked={lang === "ar"} aria-label={sh.langLabel} lang="ar"
            onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            <span className="sh-sw__track" />
            <span className="sh-sw__end sh-sw__end--en" aria-hidden="true">EN</span>
            <span className="sh-sw__end sh-sw__end--ar" aria-hidden="true">ع</span>
            <span className="sh-sw__knob sh-sw__knob--lang" aria-hidden="true">{lang === "ar" ? "ع" : "EN"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
