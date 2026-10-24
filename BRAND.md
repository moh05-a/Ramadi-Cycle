# Ramadi-Cycle brand

Tokens, React components and the living style guide (dark mode, RTL, charts, copy) are in [`brand-kit/`](brand-kit/). Run `npm run dev` there.

## Name

**Ramadi-Cycle** in English, **رمادي** in Arabic. *Ramadi* means grey: greywater (المياه الرمادية), and the grey concrete roofs that catch the rain. Always write the Arabic name next to the English one on first use. Never translate it, never abbreviate it to "RC".

## The mark

![mark](assets/mark.svg)

A flat roof over a tank, cut through by a downpipe. The tank is half concrete grey, half water blue: the water you already have. It is built from rectangles only, so it survives a fax, a photocopy and a 16-pixel favicon.

- `assets/mark.svg`: the mark alone, for icons and small sizes
- `assets/logo.svg`: mark with English and Arabic wordmark

Don't round the corners, add gradients, add a drop of water, add leaves, or recolour the tank. Keep clear space equal to the roof bar's height on every side.

## Colour

Taken from what is on a Jordanian roof: concrete, water in a tank, olive trees, rust on an old pipe.

| Name | Hex | Use |
| --- | --- | --- |
| Ink | `#1F2A2E` | Text, roof bar in the mark |
| Concrete | `#8A8D8F` | Mark and illustrations only (too light for text) |
| Concrete light | `#E2E4E0` | Panels, sidebar |
| Plaster | `#EEEFEC` | Page background |
| Cistern | `#1E5B7A` | Primary: buttons, water in charts, links |
| Olive | `#4E6128` | Savings, passed checks |
| Rust | `#A2441E` | Safety rules and warnings only |
| Stone | `#596165` | Captions, Arabic name in the logo |

Cistern on Plaster passes WCAG AA for body text. Rust is reserved for safety, so a reader learns that rust means "read this". Safety warnings use a rust triangle next to the text, not a coloured side border. Don't use rust for decoration.

## Type

- **IBM Plex Sans** and **IBM Plex Sans Arabic** for the logo, slides and printed plans. Both are open-source (OFL) and designed as a pair, so mixed English and Arabic lines sit on the same baseline weight.
- **The app uses the system sans-serif.** It runs offline and should not fetch fonts.
- Numbers use tabular figures so columns of JOD line up.

## Voice

Write like a neighbour who happens to be a plumber.

- **Concrete numbers, not adjectives.** "Saves 6 tanker trips a year", not "significant savings".
- **Say what the app doesn't know.** "Placeholder, unverified" is a feature. It's why people can trust the rest.
- **Short sentences, active verbs.** "Fit the diverter before the tank." Not "The diverter should be installed prior to the tank inlet."
- **No hype.** No "revolutionary", "smart", "AI-powered", "empower", "seamless", "unlock". The AI is a component, not the pitch. Lead with the garden your water can grow, then the dinars and tanker trips it saves.
- **No emoji** in the product or the plans.
- **Arabic is written, not translated.** Modern Standard Arabic for plans; plain words over technical ones (مزراب, not a transliterated English term).

| Instead of | Write |
| --- | --- |
| AI-powered water optimization | Shows how much water your roof and drains can give you |
| Empowering households to save | Six fewer tanker trips a year |
| Leverage greywater solutions | Send shower water to your olive tree |
| Smart blueprint | Build plan |

## Layout

Numbers first, text second. A metric row, then charts, then words. The app should read like a utility bill that got good news, not like a chat window. Flat colour, thin rules, no shadows, no rounded cards, no glassmorphism.
