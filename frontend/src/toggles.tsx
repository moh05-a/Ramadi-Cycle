// Round outline buttons for theme and language. The sun/moon paths come from the "animated theme toggle" design;
// the motion is CSS (stroke drawing + scale), so no animation library is needed. Styles: toggles.css.
import type { Lang } from "@brand";
import type { Theme } from "./theme";

const SUN = [
  "M12.4058 17.7625C15.1672 17.7625 17.4058 15.5239 17.4058 12.7625C17.4058 10.0011 15.1672 7.76251 12.4058 7.76251C9.64434 7.76251 7.40576 10.0011 7.40576 12.7625C7.40576 15.5239 9.64434 17.7625 12.4058 17.7625Z",
  "M12.4058 1.76251V3.76251", "M12.4058 21.7625V23.7625", "M4.62598 4.98248L6.04598 6.40248", "M18.7656 19.1225L20.1856 20.5425",
  "M1.40576 12.7625H3.40576", "M21.4058 12.7625H23.4058", "M4.62598 20.5425L6.04598 19.1225", "M18.7656 6.40248L20.1856 4.98248",
];
const MOON = "M21.1918 13.2013C21.0345 14.9035 20.3957 16.5257 19.35 17.8781C18.3044 19.2305 16.8953 20.2571 15.2875 20.8379C13.6797 21.4186 11.9398 21.5294 10.2713 21.1574C8.60281 20.7854 7.07479 19.9459 5.86602 18.7371C4.65725 17.5283 3.81774 16.0003 3.4457 14.3318C3.07367 12.6633 3.18451 10.9234 3.76526 9.31561C4.346 7.70783 5.37263 6.29868 6.72501 5.25307C8.07739 4.20746 9.69959 3.56862 11.4018 3.41132C10.4052 4.75958 9.92564 6.42077 10.0503 8.09273C10.175 9.76469 10.8957 11.3364 12.0812 12.5219C13.2667 13.7075 14.8384 14.4281 16.5104 14.5528C18.1823 14.6775 19.8435 14.1979 21.1918 13.2013Z";

export function ThemeToggle({ theme, onToggle, label }: { theme: Theme; onToggle: () => void; label: string }) {
  const dark = theme === "dark";
  return (
    <button type="button" role="switch" aria-checked={dark} aria-label={label} onClick={onToggle}
      className={`tg sh-sw--theme ${dark ? "is-dark" : ""}`}>
      <svg width="20" height="20" viewBox="0 0 25 25" fill="none" aria-hidden="true">
        <g className="tg__sun">{SUN.map((d) => <path key={d} d={d} pathLength={1} />)}</g>
        <path className="tg__moon" d={MOON} pathLength={1} />
      </svg>
    </button>
  );
}

/** Shows the language you switch TO; the two labels slide and fade past each other. */
export function LangToggle({ lang, onToggle, label }: { lang: Lang; onToggle: () => void; label: string }) {
  const ar = lang === "ar";
  return (
    <button type="button" role="switch" aria-checked={ar} aria-label={label} onClick={onToggle}
      className={`tg tg--lang sh-sw--lang ${ar ? "is-ar" : ""}`}>
      <span className="tg__label tg__label--en" lang="en" aria-hidden="true">EN</span>
      <span className="tg__label tg__label--ar" lang="ar" aria-hidden="true">ع</span>
    </button>
  );
}
