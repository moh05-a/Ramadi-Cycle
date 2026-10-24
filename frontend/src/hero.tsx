// Home hero: a giant brand word that rises in word by word, a short pitch and one pill button down to the form.
// Plain CSS (hero.css), no network: the background is drawn in CSS so the app still works offline.
import { useEffect, useState, type CSSProperties } from "react";
import type { Lang } from "@brand";
import { ArrowIcon } from "./icons";
import { href } from "./router";
import { SHELL } from "./v5copy";

// shortcut: no video, because a remote one breaks offline use. To add one, put a file in frontend/public
// (for example hero.mp4) and set this to "./hero.mp4".
const HERO_VIDEO = "";

/** Words rise in one after another. CSS does the motion, and prefers-reduced-motion turns it off. */
function WordsPullUp({ text, start = 0 }: { text: string; start?: number }) {
  return (
    <>
      {text.split(" ").map((word, i) => (
        <span key={i} className="hero-word" style={{ "--d": `${start + i * 80}ms` } as CSSProperties}>{word}</span>
      ))}
    </>
  );
}

export function Hero({ lang }: { lang: Lang }) {
  const sh = SHELL[lang];
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero__frame">
        {HERO_VIDEO
          ? <video className="hero__video" src={HERO_VIDEO} autoPlay loop muted playsInline aria-hidden="true" />
          : (
            <div className="hero__rain" aria-hidden="true">
              <span className="hero__drops hero__drops--far" />
              <span className="hero__drops hero__drops--near" />
            </div>
          )}
        <div className="hero__glow" aria-hidden="true" />
        <div className="hero__grain" aria-hidden="true" />
        <div className="hero__shade" aria-hidden="true" />

        <div className="hero__content">
          <h1 id="hero-title" className="hero__word" tabIndex={-1}>
            <WordsPullUp text={sh.brand} />
            <span className="sh-sr">: {sh.title}</span>
          </h1>
          <div className="hero__side">
            <p className="hero__tag rise" style={{ "--d": "350ms" } as CSSProperties}>{sh.heroTag}</p>
            <p className="hero__lead rise" style={{ "--d": "450ms" } as CSSProperties} aria-hidden="true">{sh.title}</p>
            <p className="hero__intro rise" style={{ "--d": "550ms" } as CSSProperties}>{sh.intro}</p>
            <a className="hero__cta rise" style={{ "--d": "700ms" } as CSSProperties} href={href("home")}>
              {sh.heroCta}
              <span className="hero__cta-dot"><ArrowIcon /></span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * True while the hero is under the sticky top bar, so the bar can turn transparent and sit over it.
 * Also publishes the bar's real height as --bar-h, which the hero uses to slide up beneath it.
 */
export function useOverHero(active: boolean) {
  const [over, setOver] = useState(active);
  useEffect(() => {
    const bar = document.querySelector<HTMLElement>(".sh-bar");
    const setHeight = () => document.documentElement.style.setProperty("--bar-h", `${bar?.offsetHeight ?? 80}px`);
    setHeight();
    window.addEventListener("resize", setHeight);
    if (!active) { setOver(false); return () => window.removeEventListener("resize", setHeight); }
    const frame = document.querySelector(".hero__frame");
    if (!frame) return () => window.removeEventListener("resize", setHeight);
    // over the hero until its bottom edge passes under the bar
    const io = new IntersectionObserver(([e]) => setOver(e.isIntersecting),
      { rootMargin: `-${bar?.offsetHeight ?? 80}px 0px 0px 0px` });
    io.observe(frame);
    return () => { io.disconnect(); window.removeEventListener("resize", setHeight); };
  }, [active]);
  return over;
}
