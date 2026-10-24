# Ramadi-Cycle brand kit

Design tokens, React components and a living style guide for Ramadi-Cycle (رمادي). Every component works in English (LTR) and Arabic (RTL), in light and dark themes.

```bash
npm install
npm run dev      # style guide at http://localhost:5173
npm test         # token sync, WCAG contrast, chart scale
npm run build    # static style guide in dist/
```

## Use it

```tsx
import { Button, Metric, MetricRow, SafetyBadge, copy, units } from "./brand-kit/src";

<div className="rc-root" dir={lang === "ar" ? "rtl" : "ltr"} lang={lang}>
  <MetricRow>
    <Metric label="Saved" value={256} unit={units[lang].jod + units[lang].yr} />
  </MetricRow>
  <SafetyBadge passed={6} total={6} label={copy.passed[lang]} ofWord={copy.of[lang]} />
  <Button>{copy.generate[lang]}</Button>
</div>
```

Importing `src/index.ts` loads `tokens.css` and `components.css`. The theme follows the system; set `data-theme="light"` or `"dark"` on `<html>` to force one.

| Export | What it is |
| --- | --- |
| `tokens` | Colour (light and dark), fonts, type scale, spacing, `contrast()` |
| `Mark`, `Logo` | The mark and the English and Arabic lockup |
| `Button`, `SelectField`, `SliderField`, `Toggle`, `Tabs` | Controls. Tabs follow WAI-ARIA, and arrow keys follow reading direction |
| `Metric`, `MetricRow`, `BomTable` | Numbers with units and the priced bill of materials |
| `SafetyBadge`, `Warning`, `Notice` | Status. Never colour alone |
| `MonthlyBars`, `TankLine` | Charts. Time always runs January to December, left to right |
| `copy`, `units`, `months`, `num` | English and Arabic strings, Levantine month names, Western digits |

## Rules

- `src/tokens.ts` holds the values. If you change one, change `src/tokens.css` too, or `npm test` fails.
- Every text colour must pass WCAG AA in both themes. The tests check this.
- Use logical CSS properties only (`inline-start`, not `left`).
- The Streamlit app stays offline and doesn't load these fonts. Keep `.streamlit/config.toml` in sync with the light tokens.

See `../BRAND.md` for the name, voice and logo rules in short.
