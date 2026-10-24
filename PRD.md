# Ramadi-Cycle (رمادي): Product Requirements

Owner: @Yousef · Version 1.1 · 24 Oct 2026 · Status: hackathon prototype

## 1. Problem

Households in Jordan get municipal water about once a week. When the roof tank runs dry, they buy a tanker load (صهريج). Meanwhile shower, sink and laundry water goes to the sewer, and winter rain runs off flat concrete roofs into the street.

Many of these homes have a strip of garden, a courtyard or a roof terrace they would like to plant: an olive tree, some shade, fruit for the children. Most don't, because summer water is the hard limit and nobody can tell them what their own water can keep alive through August. Garden advice is generic, plumbers quote by the job, and nobody connects the water a household already throws away to what it could grow.

Families don't act because they don't know three things: what their greywater could grow, what it would save in dinars and tanker trips, and what to buy to make it work.

## 2. Users

**Primary: a homeowner in Amman, Irbid, Zarqa or Salt** with some garden, courtyard or terrace space, a flat roof and a tanker bill they resent. Wants something green that survives summer. Comfortable with a laptop, not with plumbing or agronomy. Reads Arabic first, often English too.

**Secondary: a local plumber or handyman** who receives the downloaded plan and needs a parts list they can price.

**Not in scope for v1:** renters in apartments without roof or ground access, farms, commercial buildings.

## 3. Goal

A homeowner goes from "I don't know what my water can grow" to a garden designed for their own water, checked for every month, with the savings and a priced, safe build plan they can hand to a plumber, in under five minutes, with no internet connection.

| Measure | Target for the demo |
| --- | --- |
| Time from opening the app to a checked garden and downloaded plan | Under 5 minutes |
| AI gardens shown that pass every check (water in every month, space, greywater-safe plants, banned words) | 100% (a failed design shows no plants, never a made-up garden) |
| Numbers that trace to a visible source or assumption | 100% |
| Network calls at runtime | 0 (except Ollama on the same machine) |
| Tests passing on a clean install | All |

## 4. What the product does

1. The user describes the household: governorate, roof area, people, showers per person, laundry loads, rain tank size, budget, year type, language.
2. The engine runs a 12-month water balance: greywater every day, plus a rain tank that serves toilet flushing and cleaning and overflows to the garden in winter.
3. **Your garden.** The page shows the garden's water in its driest month, the soil and the air humidity. The user gives the garden size and, in their own words, what they want from it. **Design my garden** asks a local model to pick plants and counts. Code checks the design against every month's water, the space, the greywater-safe plant list and the banned words; a rejected design goes back to the model with the reason, up to three attempts. A passing design shows plant cards, a monthly water chart, care steps, the checks and every attempt. If none passes, the app says why and shows no plants.
4. **Savings** shows water reused, tanker trips avoided, JOD saved, kg CO₂ cut and payback, the tank level by month, the Sareef counter (before/after toggle) and a neighbourhood scale-up.
5. **Build plan** gives steps, a priced bill of materials, fixed warnings, a safety badge and a Markdown download. A model can write it; if the model is missing or fails twice, a fixed template plan is shown with a notice saying so. The template plan suggests no plants.
6. **How we calculated** shows the rules, formulas, schema, model and prompt, and every data table with its source and status.

## 5. Requirements

### Must (MVP)

| ID | Requirement | Acceptance |
| --- | --- | --- |
| G1 | Monthly garden water: greywater every day plus rain-tank overflow | Unit test: supply equals greywater per day × days + overflow |
| G2 | Plant water need per month: (ET₀ × Kc − effective rain) × canopy ÷ drip efficiency, from sourced tables | Unit tests on the formula, deciduous winter, effective-rain formula |
| G3 | Model returns JSON matching the `GardenPlan` schema; plant IDs only from `garden_plants.csv` | Schema passed to Ollama as `format`; at most 6 plant kinds, exactly 3 care steps |
| G4 | Reject a garden that runs dry in any month, exceeds the garden area, repeats a plant, uses a plant that can't take greywater, or contains banned terms | Unit test for each rejection code |
| G5 | A rejected garden goes back to the model with the reason; at most three attempts; transport errors stop at once | Unit test: the second prompt carries the first rejection |
| G6 | No plant suggestion that didn't come from a model and pass every check | No model or no passing plan returns no plan; the template build plan has no plants |
| G7 | Monthly ET₀, humidity and soil per governorate from open data, refreshed by a script, read offline | `scripts/fetch_climate.py`; tables cover every governorate in `rainfall.csv` |
| M1 | Monthly water balance with tank cap, overflow and shortfall | Unit tests: cap, no negatives, mass balance, dry < average < wet |
| M2 | Greywater recovery from shower, laundry and bathroom sink only | No kitchen or toilet source exists in the formula or catalog |
| M3 | Impact: trips, JOD, CO₂, payback from catalog cost | Payback is "n/a" when savings are zero, never a division error |
| M4 | Sareef counter before/after toggle | Toggle changes trips, JOD and CO₂ with signed deltas |
| M5 | Model returns JSON matching the `Blueprint` schema | Schema enforced by Pydantic and passed to Ollama as `format` |
| M6 | Reject unknown item IDs, out-of-budget items, non-greywater plants, quantities outside 1 to 50, banned terms | Unit tests for each |
| M7 | Two retries, then template fallback with on-screen notice (build plan) | Unit test with a fake model that returns prose |
| M8 | First-flush diverter and non-potable labels in every build plan | Added by code if the model omits them |
| M9 | Fixed warnings and disclaimer on every plan, garden and download, in the plan's language | Unit test on the Markdown output |
| M10 | English and Arabic garden and build plan, Arabic rendered right-to-left | Native speaker review before demo |
| M11 | Every constant in a CSV with source and status, shown in the app | How-we-calculated page lists all of them |
| M12 | Works with Wi-Fi off; the app runs without Ollama (no plant suggestions then) | No-model path tested |

### Should

| ID | Requirement |
| --- | --- |
| S1 | Model selector listing installed Ollama models |
| S2 | Community scale-up slider (1 to 1,000 homes) |

### Won't (v1)

Roof or garden photo analysis, maps, accounts, cloud services by default, apartment and shared-roof mode, live price feeds, planting layouts drawn to scale.

## 6. AI boundary

| Task | Owner |
| --- | --- |
| Every number: rainfall, balance, garden water, plant water needs, trips, JOD, CO₂, payback | Python |
| Which plants may take greywater | `plants.csv` |
| Plant crop factors, size and salt tolerance | `garden_plants.csv` |
| Evaporation, humidity and soil | `et0.csv`, `humidity.csv`, `soil.csv` |
| Prices and quantity limits | `catalog.csv` |
| Safety warnings, disclaimer, banned terms, watering pattern by soil | Hard-coded in `ramadi.py` |
| Designing the garden from the family's wishes: which plants, how many, why | Local model |
| Picking catalog items, ordering build steps, explaining why | Local model |
| Accepting or rejecting model output | Validation code |

The model is told not to write safety advice. If it mentions chemicals or drinking anyway, the output is rejected. This is deliberate: a plan that says "not for drinking" gets rejected too, and the fixed warning says it instead. False rejections cost a retry; false acceptances could cost someone's health. A garden that the water cannot carry through August is rejected for the same reason: a dead tree is worse than no suggestion.

## 7. Model

Any model Ollama can serve. Target a small open-weight model (Gemma, Llama or Qwen) and choose on the demo laptop by two tests: a garden design that passes the checks within three attempts in under a minute or two, and Arabic a native speaker accepts. If Arabic is weak, prompt for Modern Standard Arabic; if still weak, demo in English. The garden prompt is kept short, with the fixed part first, so a CPU-only laptop answers quickly.

## 8. Design decisions

- **Garden first, plumbing second.** The garden is what a family wants; the savings and the build plan are how they get there and what it is worth.
- **Two files, not one.** `ramadi.py` holds engine, garden planner, schemas, safety and model calls so tests import it without starting a UI. `app.py` and `api.py` hold no logic.
- **Plants only from a model.** No template garden: a made-up planting list would look like advice nobody checked. The build-plan template keeps the plumbing, without plants.
- **Water needs at full size.** Plants are sized for maturity, so a garden that fits today keeps fitting as it grows.
- **Laundry is per household**, not per person as in the original brief formula. Loads are counted per home.
- **Demand served by the rain tank** is non-potable indoor use (toilet flushing, floor cleaning). Greywater and tank overflow go to the garden.
- **Tank starts empty in January.** Conservative; the chart shows it.
- **Payback before generation** uses the template plan's cost for the chosen budget, so savings work with no model.
- **No web fonts in the app.** Offline use beats brand fidelity. Plex is used in the logo, slides and print.

## 9. Open data risks

Highest impact first:

1. Plant crop factors for fig and pomegranate, and mature plant sizes (drive what the garden can hold)
2. Household water-use figures: litres per shower, laundry load and sink (drive garden water and savings)
3. Tanker price, volume and diesel per trip (drive trips, JOD and CO₂)
4. Rainfall for the five governorates without station values (drive winter garden water)
5. Catalog prices (drive payback)
6. Greywater storage window and Jordanian reuse rules (drive a fixed warning)

The app shows each value's status so a challenged number can be answered on the spot.

## 10. Release checklist

- [ ] All tests pass on a clean install
- [ ] Chosen model pulled, warmed up, and one English and one Arabic garden designed on the demo laptop
- [ ] Arabic garden and plan read by a native speaker
- [ ] Full flow run with Wi-Fi off
- [ ] Top three data risks sourced, or flagged out loud in the pitch
- [ ] Repo public with `hacktoberfest` topic and five good first issues
