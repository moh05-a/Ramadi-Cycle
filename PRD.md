# Ramadi-Cycle (رمادي): Product Requirements

Owner: @Yousef · Version 1.0 · 24 Oct 2026 · Status: hackathon prototype

## 1. Problem

Households in Jordan get municipal water about once a week. When the roof tank runs dry, they buy a tanker load (صهريج) for 20 to 30 JOD. Meanwhile, winter rain runs off flat concrete roofs into the street, and shower and laundry water goes to the sewer while clean water flushes toilets.

Families don't act on this because they don't know three things: how much water their roof and drains could give them, what that is worth in dinars, and what to buy. Plumbers quote by the job, not by the payoff.

All figures above come from the team brief and are unverified. See section 9.

## 2. Users

**Primary: a homeowner in Amman, Irbid, Zarqa or Salt** with a flat roof, a rooftop or underground tank, some garden or tree space, and a tanker bill they resent. Comfortable with a laptop, not with plumbing. Reads Arabic first, often English too.

**Secondary: a local plumber or handyman** who receives the downloaded plan and needs a parts list they can price.

**Not in scope for v1:** renters in apartments without roof access, farms, commercial buildings.

## 3. Goal

A homeowner goes from "I don't know" to a priced, safe plan they can hand to a plumber, in under five minutes, with no internet connection.

| Measure | Target for the demo |
| --- | --- |
| Time from opening the app to downloaded plan | Under 5 minutes |
| Numbers that trace to a visible assumption | 100% |
| Generated plans that pass the safety checks before display | 100% (anything else falls back to the template) |
| Network calls at runtime | 0 |
| Tests passing on a clean install | All |

## 4. What the product does

1. The user describes the household in the sidebar: governorate, roof area, people, showers per person, laundry loads, harvest tank size, budget, year type, blueprint language.
2. The engine runs a 12-month water balance for a rain tank that serves toilet flushing and cleaning, plus weekly greywater recovery for trees.
3. The header shows water reused, tanker trips avoided, JOD saved, kg CO₂ cut and payback.
4. The **Impact** tab shows tank level by month, rain vs still-bought demand, and the Sareef counter (before/after toggle).
5. **Generate blueprint** asks a local model to pick parts from the catalog and write steps. Code validates, prices and safety-checks the result. If the model is missing or fails twice, a fixed template plan is shown with a notice saying so.
6. The **Blueprint** tab shows steps, priced bill of materials, plants, fixed warnings, a safety badge and a Markdown download.
7. **Safety & method** shows the rules, formulas, schema, model and prompt. **Assumptions & sources** shows every constant and its status.

## 5. Requirements

### Must (MVP)

| ID | Requirement | Acceptance |
| --- | --- | --- |
| M1 | Monthly water balance with tank cap, overflow and shortfall | Unit tests: cap, no negatives, mass balance, dry < average < wet |
| M2 | Greywater recovery from shower, laundry and bathroom sink only | No kitchen or toilet source exists in the formula or catalog |
| M3 | Impact: trips, JOD, CO₂, payback from catalog cost | Payback is "n/a" when savings are zero, never a division error |
| M4 | Sareef counter before/after toggle | Toggle changes trips, JOD and CO₂ with signed deltas |
| M5 | Model returns JSON matching the `Blueprint` schema | Schema enforced by Pydantic and passed to Ollama as `format` |
| M6 | Reject unknown item IDs, out-of-budget items, non-greywater plants, quantities outside 1 to 50, banned terms | Unit tests for each |
| M7 | Two retries, then template fallback with on-screen notice | Unit test with a fake model that returns prose |
| M8 | First-flush diverter and non-potable labels in every plan | Added by code if the model omits them |
| M9 | Fixed warnings and disclaimer on every plan and download, in the plan's language | Unit test on the Markdown output |
| M10 | English and Arabic blueprint, Arabic rendered right-to-left | Native speaker review before demo |
| M11 | Every constant in a CSV with source and status, shown in the app | Assumptions tab lists all of them |
| M12 | Works with Wi-Fi off; app runs without Ollama | Template path tested |

### Should

| ID | Requirement |
| --- | --- |
| S1 | Model selector listing installed Ollama models |
| S2 | Community scale-up slider (1 to 1,000 homes) |

### Won't (v1)

Roof-photo analysis, maps, accounts, cloud services, apartment and shared-roof mode, live price feeds.

## 6. AI boundary

| Task | Owner |
| --- | --- |
| Every number: rainfall, balance, trips, JOD, CO₂, payback | Python |
| Prices and quantity limits | `catalog.csv` |
| Which plants may take greywater | `plants.csv` |
| Safety warnings, disclaimer, banned terms | Hard-coded in `ramadi.py` |
| Picking catalog items, ordering steps, explaining why | Local model |
| Accepting or rejecting model output | Validation code |

The model is told not to write safety advice. If it mentions chemicals or drinking anyway, the output is rejected. This is deliberate: a plan that says "not for drinking" gets rejected too, and the fixed warning says it instead. False rejections cost a retry; false acceptances could cost someone's health.

## 7. Model

Any model Ollama can serve. Target a ~4B open-weight model (Gemma, Llama or Qwen) and choose on the demo laptop by two tests: a full blueprint in under 30 seconds, and Arabic a native speaker accepts. If Arabic is weak, prompt for Modern Standard Arabic; if still weak, demo in English.

## 8. Design decisions

- **Two files, not one.** `ramadi.py` holds engine, schema, safety and model call so tests import it without starting Streamlit. `app.py` is UI only.
- **Laundry is per household**, not per person as in the original brief formula. Loads are counted per home.
- **Demand served by the rain tank** is non-potable indoor use (toilet flushing, floor cleaning) at a placeholder 30 L per person per day. Greywater goes to trees.
- **Tank starts empty in January.** Conservative; the chart shows it.
- **Payback before generation** uses the template plan's cost for the chosen budget, so the Impact tab works with no model.
- **No web fonts in the app.** Offline use beats brand fidelity. Plex is used in the logo, slides and print.

## 9. Open data risks

Every constant is a placeholder until sourced. Highest impact first:

1. Tanker price, volume and diesel per trip (drive trips, JOD and CO₂)
2. Rainfall by governorate and monthly shares (drive all rain numbers)
3. Non-potable demand per person
4. Catalog prices (drive payback)
5. Greywater storage window and Jordanian reuse rules (drive a fixed warning)

The app shows each value's status so a challenged number can be answered on the spot.

## 10. Release checklist

- [ ] All tests pass on a clean install
- [ ] Chosen model pulled and warmed up on the demo laptop
- [ ] Arabic plan read by a native speaker
- [ ] Full flow run with Wi-Fi off
- [ ] Top three data risks sourced, or flagged out loud in the pitch
- [ ] Repo public with `hacktoberfest` topic and five good first issues
