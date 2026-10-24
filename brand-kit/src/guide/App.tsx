import { useEffect, useState, type ReactNode } from "react";
import tokensCss from "../tokens.css?raw";
import {
  BomTable, Button, Logo, Mark, Metric, MetricRow, MonthlyBars, Notice, SafetyBadge, SelectField, SliderField,
  TankLine, Tabs, Toggle, Warning, copy, months, num, tokens, units, type Lang,
} from "../index";

const { color, contrast, space, text } = tokens;

const SECTIONS = [
  ["logo", "Logo"], ["colour", "Colour"], ["type", "Type"], ["layout", "Layout & spacing"], ["components", "Components"],
  ["charts", "Charts"], ["arabic", "Arabic & RTL"], ["voice", "Voice & copy"], ["a11y", "Accessibility"], ["usage", "Use in code"],
] as const;

type Theme = "system" | "light" | "dark";

export function App() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <div className="rc-root g-page">
      <a className="g-skip" href="#main">Skip to content</a>
      <nav className="g-nav" aria-label="Sections">
        <Mark size={36} />
        <ul>{SECTIONS.map(([id, label]) => <li key={id}><a href={`#${id}`}>{label}</a></li>)}</ul>
        <Segmented label="Theme" value={theme} onChange={setTheme} options={[["system", "System"], ["light", "Light"], ["dark", "Dark"]]} />
      </nav>
      <main id="main" className="g-main">
        <Hero />
        <LogoSection />
        <ColourSection />
        <TypeSection />
        <LayoutSection />
        <ComponentsSection />
        <ChartsSection />
        <ArabicSection />
        <VoiceSection />
        <A11ySection />
        <UsageSection />
      </main>
    </div>
  );
}

function Segmented<T extends string>({ label, value, onChange, options }: { label: string; value: T; onChange: (v: T) => void; options: [T, string][] }) {
  return (
    <div className="g-seg" role="group" aria-label={label}>
      {options.map(([v, l]) => <button key={v} type="button" aria-pressed={v === value} onClick={() => onChange(v)}>{l}</button>)}
    </div>
  );
}

function Section({ id, title, meta, children }: { id: string; title: string; meta?: string; children: ReactNode }) {
  return (
    <section id={id} className="g-section" aria-labelledby={`h-${id}`}>
      <header className="g-section__head"><h2 id={`h-${id}`}>{title}</h2>{meta && <code>{meta}</code>}</header>
      {children}
    </section>
  );
}

function Rules({ items, dont = false }: { items: ReactNode[]; dont?: boolean }) {
  return <ul className={`g-rules ${dont ? "is-dont" : ""}`}>{items.map((it, i) => <li key={i}>{it}</li>)}</ul>;
}

function CopyButton({ text: value, label = "Copy" }: { text: string; label?: string }) {
  const [state, setState] = useState(label);
  const onClick = async () => {
    try { await navigator.clipboard.writeText(value); setState("Copied"); } catch { setState("Copy failed: select the text"); }
    setTimeout(() => setState(label), 1400);
  };
  return <button type="button" className="g-copy" onClick={onClick} aria-live="polite">{state}</button>;
}

function Hero() {
  return (
    <header className="g-hero">
      <Mark size={120} />
      <div className="g-hero__text">
        <p className="g-label">Brand kit · v1.0 · October 2026</p>
        <h1>Ramadi-Cycle <span lang="ar">رمادي</span></h1>
        <p className="g-lede"><i>Ramadi</i> means grey: greywater (<span lang="ar">المياه الرمادية</span>) and the grey concrete roofs that catch the rain. These are the tokens, React components and rules for building Ramadi-Cycle screens in English and Arabic.</p>
        <dl className="g-facts">
          <div><dt>Primary</dt><dd>Cistern blue</dd></div>
          <div><dt>Type</dt><dd>IBM Plex Sans + Arabic</dd></div>
          <div><dt>Radius</dt><dd>2px, panels square</dd></div>
          <div><dt>Shadows</dt><dd>None</dd></div>
          <div><dt>Themes</dt><dd>Light and dark</dd></div>
        </dl>
      </div>
    </header>
  );
}

function LogoSection() {
  return (
    <Section id="logo" title="Logo" meta="<Mark /> · <Logo />">
      <p>A flat roof over a tank, joined by a downpipe. The tank is half concrete, half water: the water a household already has. It uses only rectangles, so it holds up on a photocopied plan and as a 16px favicon.</p>
      <div className="g-grid">
        <figure className="g-tile"><div className="g-tile__art"><Mark size={96} /></div><figcaption><b>Mark.</b> Follows the theme. Favicon, app icon, slide corner.</figcaption></figure>
        <figure className="g-tile is-dark"><div className="g-tile__art"><Mark size={96} reversed /></div><figcaption><b>Reversed.</b> Fixed colours for photos and dark print.</figcaption></figure>
        <figure className="g-tile"><div className="g-tile__art"><Logo width={230} /></div><figcaption><b>Lockup.</b> Headers, README, title slides.</figcaption></figure>
      </div>
      <div className="g-two">
        <div className="g-stack">
          <h3>Clear space and minimum size</h3>
          <p className="g-lede">Leave clear space equal to the roof bar's height on every side. The mark can go down to 16px; the lockup needs at least 120px of width.</p>
          <div className="g-sizes">
            <span className="g-clear"><Mark size={64} /></span>
            {[32, 24, 16].map((s) => <figure key={s}><Mark size={s} title="" />{s}px</figure>)}
          </div>
        </div>
        <div className="g-stack">
          <h3>Don't</h3>
          <Rules dont items={["Round the corners or add a drop shadow.", "Add gradients, water drops or leaves.", "Recolour the water or swap the tank halves.", "Skew, stretch or outline it.", "Translate the name, drop the hyphen or shorten it to \"RC\"."]} />
        </div>
      </div>
    </Section>
  );
}

function ColourSection() {
  const fg = ["ink", "stone", "cistern", "olive", "rust"] as const;
  return (
    <Section id="colour" title="Colour" meta="--rc-*">
      <p>The palette comes from a Jordanian roof: concrete, water in a tank, olive trees, rust on an old pipe. Each chip shows the light value on the left and the dark value on the right.</p>
      <div className="g-grid">
        {(["ink", "stone", "bg", "surface", "paper", "rule", "cistern", "olive", "rust", "mark-tank"] as const).map((k) => (
          <div key={k} className="g-swatch">
            <div className="g-swatch__chip"><i style={{ background: color[k].light }} /><i style={{ background: color[k].dark }} /></div>
            <div className="g-swatch__meta">
              <b>{color[k].name}</b><code>--rc-{k}</code><span>{color[k].use}</span>
              <div className="g-row"><CopyButton text={color[k].light} label={color[k].light} /><CopyButton text={color[k].dark} label={color[k].dark} /></div>
            </div>
          </div>
        ))}
      </div>
      <Rules items={[
        <><b>Cistern is the only accent.</b> Use it for buttons, links, active tabs and the rain series.</>,
        <><b>Olive means saved or passed.</b> Use it for good-news deltas, the passed badge and greywater in charts.</>,
        <><b>Rust means safety.</b> Use it for warnings and failed checks. It is never decoration and never a second accent.</>,
        <><b>Concrete is for the logo only.</b> At {contrast(color["mark-tank"].light, color.bg.light).toFixed(1)}:1 it is too light for text or control borders.</>,
        "No gradients, no pure black, no pure white page.",
      ]} />
      <h3>Contrast, computed from the tokens</h3>
      <div className="rc-table-wrap" tabIndex={0} role="region" aria-label="Contrast ratios">
        <table className="rc-table g-contrast">
          <thead><tr><th scope="col">Text</th><th scope="col">Page, light</th><th scope="col">Panel, light</th><th scope="col">Page, dark</th><th scope="col">Panel, dark</th></tr></thead>
          <tbody>
            {fg.map((k) => (
              <tr key={k}>
                <th scope="row">{color[k].name}</th>
                {(["light", "dark"] as const).flatMap((m) => (["bg", "surface"] as const).map((b) => {
                  const r = contrast(color[k][m], color[b][m]);
                  return <td key={m + b}>{r.toFixed(2)} {r >= 7 ? "AAA" : r >= 4.5 ? "AA" : "fail"}</td>;
                }))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function TypeSection() {
  return (
    <Section id="type" title="Type" meta="--rc-font-* · --rc-text-*">
      <p>IBM Plex Sans and IBM Plex Sans Arabic were drawn as a pair. A line that mixes <span lang="ar">صهريج</span> with "tanker" keeps the same weight and rhythm. Both are open source (SIL OFL).</p>
      <div className="g-two">
        <div className="g-panel g-stack"><span className="g-label">Latin</span><p className="g-big">6 fewer tanker trips a year</p><p>Fit the first-flush diverter on the downpipe before the tank.</p></div>
        <div className="g-panel g-stack" dir="rtl" lang="ar"><span className="g-label">عربي</span><p className="g-big">6 رحلات صهريج أقل في السنة</p><p>ركّب محوّل الدفقة الأولى على ماسورة التصريف قبل الخزان.</p></div>
      </div>
      <div className="g-stack">
        {Object.entries(text).map(([k, t]) => (
          <div key={k} className="g-scale">
            <code>--rc-text-{k}<br />{t.px}px · {t.use}</code>
            <span style={{ fontSize: t.rem, fontWeight: ["3xl", "xl", "lg"].includes(k) ? 600 : k === "2xl" ? 500 : 400 }}>42.5 m³ a year · <span lang="ar">42.5 م³ في السنة</span></span>
          </div>
        ))}
      </div>
      <Rules items={[
        "Weights: 400 for body, 500 for numbers and labels, 600 for headings.",
        "Line height is 1.55 for Latin body text and 1.75 for Arabic, which needs room for marks above and below the line.",
        "Keep body text under 70 characters wide. Numbers use tabular figures.",
        "Use uppercase only for small Latin labels, with 0.06em letter-spacing. Never letter-space Arabic, and never set it in italics.",
        <><b>The Streamlit app does not load web fonts.</b> It runs offline, so it uses the system sans-serif.</>,
      ]} />
    </Section>
  );
}

function LayoutSection() {
  return (
    <Section id="layout" title="Layout & spacing" meta="--rc-space-* · --rc-radius">
      <p>Put numbers first, charts second and words third. A screen should read like a utility bill that brings good news, not like a chat window.</p>
      <div className="g-two">
        <div className="g-stack">
          {Object.entries(space).map(([k, px]) => (
            <div key={k} className="g-space"><code>--rc-space-{k}</code><code>{px}px</code><i style={{ inlineSize: px * 3 }} /></div>
          ))}
        </div>
        <Rules items={[
          "Separate things with flat colour and 1px rules. No shadows, blur or glass.",
          "Controls get a 2px radius. Panels and tables are square.",
          "Box content only where it helps: tables, code, forms.",
          "Screen order is sidebar inputs, then the metric row, then tabs.",
          "Keep content under 1180px wide, with a side gutter of at least 16px on phones.",
          "Animate state changes only, at 120ms ease-out. No entrance animations.",
        ]} />
      </div>
    </Section>
  );
}

const EX = { level: [2, 2, 2, 0.3, 0, 0, 0, 0, 0, 0, 0, 2], rain: [4.6, 4.6, 4.6, 4.6, 1.2, 0, 0, 0, 0, 1.8, 4.6, 4.6], grey: 4.5, demand: 9.2 };

function ComponentsSection() {
  const [lang, setLang] = useState<Lang>("en");
  const [gov, setGov] = useState("irbid");
  const [roof, setRoof] = useState(120);
  const [after, setAfter] = useState(true);
  const [tab, setTab] = useState("impact");
  const ar = lang === "ar", u = units[lang];
  const t = (en: string, arText: string) => (ar ? arText : en);
  return (
    <Section id="components" title="Components" meta="import { … } from '@ramadi-cycle/brand-kit'">
      <p>These are live React components. Switch the language to check each one in Arabic. All figures are examples.</p>
      <Segmented label="Language" value={lang} onChange={setLang} options={[["en", "English · LTR"], ["ar", "العربية · RTL"]]} />
      <div className="g-stage" dir={ar ? "rtl" : "ltr"} lang={lang}>
        <Demo name="Button">
          <div className="g-row">
            <Button>{copy.generate[lang]}</Button>
            <Button variant="secondary">{copy.download[lang]}</Button>
            <Button disabled>{t("Generating…", "جارٍ الإنشاء…")}</Button>
          </div>
        </Demo>
        <Demo name="SelectField · SliderField">
          <div className="g-fields">
            <SelectField label={t("Governorate", "المحافظة")} value={gov} onChange={setGov}
              options={[{ value: "irbid", label: t("Irbid · 470 mm/yr", "إربد · 470 ملم/سنة") }, { value: "amman", label: t("Amman (west) · 450 mm/yr", "عمّان (الغربية) · 450 ملم/سنة") }, { value: "zarqa", label: t("Zarqa · 130 mm/yr", "الزرقاء · 130 ملم/سنة") }]} />
            <SliderField label={t("Roof area", "مساحة السطح")} value={roof} min={0} max={400} step={10} unit={u.m2} onChange={setRoof}
              hint={t("Flat concrete roof you can run gutters along.", "سطح خرساني مستوٍ يمكن تركيب مزاريب على حوافه.")} />
          </div>
        </Demo>
        <Demo name="Metric · MetricRow">
          <MetricRow>
            <Metric label={t("Water reused", "مياه مُعاد استخدامها")} value={85.5} decimals={1} unit={u.m3 + u.yr} />
            <Metric label={t("Tanker trips avoided", "رحلات صهريج أقل")} value={8.5} decimals={1} unit={u.yr} />
            <Metric label={t("Saved", "التوفير")} value={256} unit={u.jod + u.yr} />
            <Metric label={t("CO₂ cut", "خفض CO₂")} value={111} unit={u.kg + u.yr} />
            <Metric label={t("Payback", "استرداد الكلفة")} value={15} unit={u.months} />
          </MetricRow>
        </Demo>
        <Demo name="Toggle · Sareef counter">
          <Toggle label={t("With Ramadi-Cycle", "مع رمادي")} checked={after} onChange={setAfter} />
          <Metric label={t("Tanker trips a year", "رحلات الصهريج في السنة")} value={after ? 2.5 : 11} decimals={1} unit=""
            delta={after ? { value: -8.5, good: true } : undefined} />
        </Demo>
        <Demo name="SafetyBadge · Notice · Warning">
          <div className="g-row">
            <SafetyBadge passed={6} total={6} label={copy.passed[lang]} ofWord={copy.of[lang]} />
            <SafetyBadge passed={5} total={6} label={copy.passed[lang]} ofWord={copy.of[lang]} />
          </div>
          <Notice>{copy.fallback[lang]}</Notice>
          <Warning>{copy.greywaterRule[lang]}</Warning>
        </Demo>
        <Demo name="Tabs">
          <Tabs active={tab} onChange={setTab} tabs={[
            { id: "impact", label: t("Impact", "الأثر"), panel: <p>{t("Tank level and the Sareef counter.", "مستوى الخزان وعدّاد الصهريج.")}</p> },
            { id: "plan", label: t("Blueprint", "خطة التنفيذ"), panel: <p>{copy.empty[lang]}</p> },
            { id: "method", label: t("Safety & method", "السلامة والطريقة"), panel: <p>{t("Fixed rules, formulas and the model prompt.", "القواعد الثابتة والمعادلات وتعليمات النموذج.")}</p> },
            { id: "data", label: t("Assumptions & sources", "الافتراضات والمصادر"), panel: <p>{t("Every constant with its source and status.", "كل ثابت مع مصدره وحالته.")}</p> },
          ]} />
        </Demo>
        <Demo name="BomTable">
          <BomTable caption={t("Placeholder prices from data/catalog.csv", "أسعار مؤقتة من data/catalog.csv")}
            labels={{ item: t("Item", "المادة"), qty: t("Qty", "الكمية"), each: t("JOD each", "دينار للقطعة"), total: u.jod, sum: t("Total", "المجموع") }}
            rows={[
              { item: t("First-flush diverter kit", "محوّل مياه الدفقة الأولى"), qty: 1, unit: "", unitJod: 15 },
              { item: t("PVC roof gutter", "مزراب بلاستيك PVC"), qty: 22, unit: t("m", "م"), unitJod: 3 },
              { item: t("1 m³ plastic storage tank", "خزان بلاستيك 1 م³"), qty: 1, unit: "", unitJod: 90 },
            ]} />
        </Demo>
      </div>
    </Section>
  );
}

function Demo({ name, children }: { name: string; children: ReactNode }) {
  return <div className="g-demo"><code className="g-demo__name" dir="ltr">{name}</code>{children}</div>;
}

function ChartsSection() {
  const [lang, setLang] = useState<Lang>("en");
  const ar = lang === "ar";
  const grey = Array(12).fill(EX.grey);
  const bought = EX.rain.map((r, i) => Math.max(0, EX.demand - r - grey[i]));
  return (
    <Section id="charts" title="Charts" meta="<MonthlyBars /> · <TankLine />">
      <p>Each chart answers one question in its title and gives the unit in brackets. The data here is an example: a 120 m² roof with a 2 m³ tank in an average year.</p>
      <Segmented label="Chart language" value={lang} onChange={setLang} options={[["en", "English"], ["ar", "العربية"]]} />
      <div className="g-two" dir={ar ? "rtl" : "ltr"} lang={lang}>
        <div className="g-panel g-stack">
          <h3>{ar ? "الطلب غير الصالح للشرب: من المطر أو مشترى (م³)" : "Non-potable demand: from rain vs still bought (m³)"}</h3>
          <MonthlyBars lang={lang} label={ar ? "أعمدة شهرية مكدسة" : "Stacked monthly bars, example data"} series={[
            { label: ar ? "من المطر" : "From rain", values: EX.rain, color: "cistern" },
            { label: ar ? "مياه رمادية" : "Greywater", values: grey, color: "olive" },
            { label: ar ? "ما زال يُشترى" : "Still bought", values: bought, color: "bought" },
          ]} />
          <p className="g-note">{ar ? "يغطي المطر نحو نصف الطلب من تشرين الثاني إلى نيسان." : "Rain covers about half the demand from November to April."}</p>
        </div>
        <div className="g-panel g-stack">
          <h3>{ar ? "مستوى خزان الحصاد شهرياً (م³)" : "Harvest tank level by month (m³)"}</h3>
          <TankLine lang={lang} level={EX.level} capacity={2} label={ar ? "خط مستوى الخزان" : "Tank level line, example data"}
            legend={ar ? ["مستوى الخزان", "السعة"] : ["Tank level", "Capacity"]} />
          <p className="g-note">{ar ? "يبدأ الخزان فارغاً في كانون الثاني." : "Tank starts empty in January."}</p>
        </div>
      </div>
      <div className="rc-table-wrap" tabIndex={0} role="region" aria-label="Chart series tokens">
        <table className="rc-table">
          <thead><tr><th scope="col">Series</th><th scope="col">Token</th><th scope="col">Mark</th></tr></thead>
          <tbody>
            <tr><td>Rain used, tank level</td><td><code>--rc-cistern</code></td><td>Bar segment; 2px line with 3px points</td></tr>
            <tr><td>Greywater reused</td><td><code>--rc-olive</code></td><td>Bar segment</td></tr>
            <tr><td>Still bought</td><td><code>--rc-bought</code></td><td>Bar segment</td></tr>
            <tr><td>Capacity, targets</td><td><code>--rc-stone</code></td><td>1px dashed rule</td></tr>
            <tr><td>Axis labels, grid</td><td><code>--rc-stone</code> · <code>--rc-rule</code></td><td>11px labels; horizontal grid only</td></tr>
          </tbody>
        </table>
      </div>
      <Rules items={[
        "Months run January to December. Set the sort order explicitly, because chart libraries sort month names alphabetically.",
        <>In Arabic, use the Levantine month names used in Jordan: <span lang="ar">{months.ar.join("، ")}</span>.</>,
        "Time runs left to right in both languages. Only titles and legends flip.",
        "Put a one-line text summary under every chart.",
        "No pie charts, 3D or dual axes. Never use rust in a chart.",
      ]} />
    </Section>
  );
}

function ArabicSection() {
  const terms: [string, string][] = [["m³", "م³"], ["JOD", "دينار"], ["Greywater", "المياه الرمادية"], ["Tanker", "صهريج"], ["Gutter", "مزراب"], ["First-flush diverter", "محوّل الدفقة الأولى"], ["Build plan", "خطة التنفيذ"]];
  return (
    <Section id="arabic" title="Arabic & RTL" meta='dir="rtl" lang="ar"'>
      <p>Most users read Arabic first. Write each Arabic string directly instead of machine-translating the English, and build every screen to work in both directions.</p>
      <div className="g-two">
        <Rules items={[
          <>Set <code>dir</code> and <code>lang</code> on the container. The components handle the rest.</>,
          <>Use logical CSS such as <code>margin-inline-start</code>, <code>border-inline-start</code> and <code>text-align: start</code>. Never use left or right for layout.</>,
          "Mirror icons that point somewhere (arrows, chevrons). Never mirror the logo, checkmarks or charts.",
          <>Use Western digits (0–9) in both languages, like Jordanian bills do. <code>num()</code> does this.</>,
          "Write plans in Modern Standard Arabic, with the trade words a plumber uses.",
          "Arrow keys in Tabs follow reading direction.",
        ]} />
        <div className="rc-table-wrap" tabIndex={0} role="region" aria-label="English and Arabic terms">
          <table className="rc-table">
            <thead><tr><th scope="col">English</th><th scope="col">Arabic</th></tr></thead>
            <tbody>{terms.map(([en, a]) => <tr key={en}><td>{en}</td><td lang="ar" dir="rtl">{a}</td></tr>)}</tbody>
          </table>
        </div>
      </div>
      <Notice>A native speaker must review all Arabic in this kit before release.</Notice>
    </Section>
  );
}

function VoiceSection() {
  const rows: [string, keyof typeof copy][] = [["Primary action", "generate"], ["Empty state", "empty"], ["Fallback", "fallback"], ["Model missing", "noModel"], ["Disclaimer", "disclaimer"]];
  return (
    <Section id="voice" title="Voice & copy">
      <p>Write like a neighbour who happens to be a plumber. Use concrete numbers and short sentences, and say plainly what the app doesn't know.</p>
      <div className="g-two">
        <div className="g-panel g-do"><span className="g-label">Write</span><p>Shows how much water your roof and drains can give you.</p><p>Six fewer tanker trips a year.</p><p>Send shower water to your olive tree.</p><p>Placeholder value. Not verified yet.</p></div>
        <div className="g-panel g-do is-dont"><span className="g-label">Don't write</span><p>AI-powered water optimization.</p><p>Empowering households to save.</p><p>Leverage greywater solutions.</p><p>Based on industry-standard assumptions.</p></div>
      </div>
      <p className="g-lede"><b>Banned words:</b> revolutionary, smart, AI-powered, empower, seamless, unlock, leverage, cutting-edge, game-changer, journey. No emoji anywhere. The model is one part of the product, not the pitch. Lead with water and dinars.</p>
      <div className="rc-table-wrap" tabIndex={0} role="region" aria-label="Microcopy in English and Arabic">
        <table className="rc-table g-copytable">
          <thead><tr><th scope="col">Moment</th><th scope="col">English</th><th scope="col">Arabic</th><th scope="col">Key</th></tr></thead>
          <tbody>{rows.map(([m, k]) => <tr key={k}><th scope="row">{m}</th><td>{copy[k].en}</td><td lang="ar" dir="rtl">{copy[k].ar}</td><td><code>copy.{k}</code></td></tr>)}</tbody>
        </table>
      </div>
      <p className="g-lede">In errors, say what happened and what to do next. Don't apologise.</p>
    </Section>
  );
}

function A11ySection() {
  return (
    <Section id="a11y" title="Accessibility" meta="WCAG 2.1 AA">
      <Rules items={[
        "Text contrast is at least 4.5:1 in both themes. The table under Colour is computed from the live tokens.",
        "Every element you can reach by keyboard shows focus: a 2px Cistern outline with a 2px offset.",
        "Touch targets are at least 44px tall: buttons, selects, toggles and tabs.",
        "Status never relies on colour alone. Badges and safety warnings have an icon and words, and chart series have a legend and a text summary.",
        "Every input has a visible label and shows its unit. Sliders announce the value with the unit.",
        "Tabs follow the WAI-ARIA pattern: roving tabindex, arrow keys, Home and End.",
        "Safety warnings are real text, never images.",
        "Transitions turn off under prefers-reduced-motion.",
      ]} />
    </Section>
  );
}

function UsageSection() {
  const usage = `import { Button, Metric, MetricRow, SafetyBadge, copy, units } from "@ramadi-cycle/brand-kit";

export function Summary({ lang }) {
  const u = units[lang];
  return (
    <div className="rc-root" dir={lang === "ar" ? "rtl" : "ltr"} lang={lang}>
      <MetricRow>
        <Metric label="Water reused" value={85.5} decimals={1} unit={u.m3 + u.yr} />
        <Metric label="Saved" value={256} unit={u.jod + u.yr} />
      </MetricRow>
      <SafetyBadge passed={6} total={6} label={copy.passed[lang]} ofWord={copy.of[lang]} />
      <Button>{copy.generate[lang]}</Button>
    </div>
  );
}`;
  return (
    <Section id="usage" title="Use in code" meta="brand-kit/src">
      <p>Importing from <code>src/index.ts</code> pulls in the tokens and component CSS. Wrap the app in <code>.rc-root</code> and set <code>dir</code> and <code>lang</code>. Theme follows the system unless you set <code>data-theme</code> on <code>&lt;html&gt;</code>.</p>
      <Code title="Example" body={usage} />
      <Code title="tokens.css" body={tokensCss} />
      <Code title="Streamlit .streamlit/config.toml" body={`[theme]\nbase = "light"\nprimaryColor = "${color.cistern.light}"\nbackgroundColor = "${color.bg.light}"\nsecondaryBackgroundColor = "${color.surface.light}"\ntextColor = "${color.ink.light}"\nfont = "sans serif"`} />
      <p className="g-note">Example figures: {num(85.5, 1)} m³, {num(256)} JOD. No real household data.</p>
    </Section>
  );
}

function Code({ title, body }: { title: string; body: string }) {
  return (
    <div className="g-code">
      <div className="g-code__head"><span className="g-label">{title}</span><CopyButton text={body} /></div>
      <pre tabIndex={0}><code>{body}</code></pre>
    </div>
  );
}
