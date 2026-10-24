# Backend audit: Ramadi-Cycle

24 Oct 2026. Scope: `ramadi.py`, `app.py`, `data/*.csv`, tests. Spec: `PRD.md` §5 (M1–M12, S1–S2).
Result: 330 tests pass with `pytest -q` in a clean venv from `requirements-dev.txt`.

## 0. Map of `ramadi.py`

Units: rain in mm (CSV) → m inside the engine; roof m²; volumes m³ (1 mm × 1 m² = 1 L = 0.001 m³); demand L/person/day; money JOD; CO₂ kg (t on the community line).

| Function | In → out | CSV columns read | PRD |
| --- | --- | --- | --- |
| `read_table`, `load_tables` | file names → checked `Tables(rain, shares, catalog, plants, assumptions)` | every column in `COLUMNS` | M11 |
| `assumption_values` | assumptions df → `{parameter: float}`, checks required params, fractions in 0–1, dry < avg < wet | assumptions `parameter, value` | M11 |
| `make_profile`, `check_profile` | sidebar values → checked profile dict (raises `InputError`) | rainfall `governorate, annual_mm` | M1 |
| `annual_potential` | m², m, fraction → m³/yr | `runoff_coefficient` | M1 |
| `water_balance` | m², m, 12 shares, k, runoff, first flush, m³ cap, 12 × m³ demand → monthly df (start, inflow, demand, met, shortfall, overflow, level, all m³) | via args | M1 |
| `greywater_week` | people, showers/person/wk, loads/wk → m³/wk | `litres_per_shower, litres_per_laundry_load, sink_litres_per_person_week, greywater_recovery` | M2 |
| `impact` | m³/yr, JOD → trips/yr, JOD/yr, kg CO₂/yr, payback months or None | `tanker_*`, `municipal_tariff`, `diesel_*`, `pump_energy`, `grid_co2` | M3 |
| `simulate` | profile, shares, a → balance + m³/yr totals | `year_multiplier_*`, `nonpotable_litres_per_person_day`, `first_flush_loss` | M1, M2 |
| `format_payback` | months or None → "N months" or "n/a" | | M3 |
| `sareef` | result, a, toggle → before/now/delta of trips, JOD, kg CO₂ | | M4 |
| `community` | result, impact, homes 1–1000 → m³, trips, t CO₂ | | S2 |
| `PlanItem`, `PlantPick`, `Blueprint` | strict, closed schema | | M5 |
| `normalise`, `find_banned`, `clean_model_text` | text → normalised text / first banned term / JSON text | | M6, M7 |
| `validate` | raw model output → `(Blueprint, None)` or `(None, Rejection(code, detail))` | catalog `item_id, budget_level, price_jod`; plants `plant_id, greywater_ok` | M6 |
| `enforce_required` | Blueprint → Blueprint with first-flush and labels | | M8 |
| `safety_checks` | Blueprint → badge rows | | M6, M8, M9 |
| `price`, `plan_cost` | Blueprint → BOM df (JOD) → total JOD | catalog `name_en/ar, unit, price_jod` | M3 |
| `template_blueprint` | profile, budget, lang → Blueprint | | M7, M12 |
| `list_models`, `ollama_chat`, `as_model_error` | local Ollama HTTP → model names / reply text / typed `ModelError` | | S1, M5, M12 |
| `build_prompt` | profile, results, tables → prompt text | catalog, plants | M5 |
| `generate`, `fallback_notice` | → `Generation(blueprint, source, notes)` / notice text | | M7 |
| `to_markdown` | Blueprint, BOM → Markdown (RTL block for Arabic) | | M9, M10 |

No implementing code: **M10** (native-speaker review is a process step). Code with no requirement: the municipal-tariff and pump-energy terms in `impact`, the `potential` caption figure, and the template's sizing rule (gutter = 2√roof m, clamped 4–50).

## 1. Checks

Status is as found before any change. Commits are on `main`.

| ID | Check | Found | Line (before) | Fixed in | Test(s) |
| --- | --- | --- | --- | --- | --- |
| M1.1 | Harvest = rain × roof × runoff × (1 − first flush), coefficient from CSV | PASS | ramadi.py:43 | n/a | `test_harvest_is_one_litre_per_mm_per_m2`, `test_year_multiplier_applied_once` |
| M1.2 | Monthly shares sum to 1, fail loudly on load | FAIL: no check at load | ramadi.py:22 | 6a36d59 | `test_shares_sum_to_one`, `test_loader_fails_loudly[monthly_share…]` |
| M1.3 | Demand uses real days per month | FAIL: × 30.4 | ramadi.py:74 | d337760 | `test_demand_uses_real_days_per_month` |
| M1.4 | Tank starts empty; 0 ≤ level ≤ cap; overflow, shortfall ≥ 0 | PASS | ramadi.py:41–47 | n/a | `test_balance_invariants` (hypothesis) |
| M1.5 | Mass balance every month | PASS in code, tested only as a yearly sum, no start column | ramadi.py:39 | d337760 (adds `start`, derives overflow) | `test_balance_invariants` |
| M1.6 | Year multiplier applied once; dry < avg < wet | PASS (strict for inflow/potential; outputs capped by demand or tank can only be ≤) | ramadi.py:72–81 | 6a36d59 (CSV order checked) | `test_dry_le_average_le_wet`, `test_year_multiplier_applied_once` |
| M1.7 | Zero roof/tank/people give zeros, not errors or NaN | PASS for zeros; FAIL because nothing rejected negatives, NaN or an unknown year. "Budget 0" is n/a (budget is a level, not a number) | ramadi.py:70 | d337760, afa1bb2 | `test_zero_inputs_give_zeros_not_errors`, `test_bad_inputs_raise_input_error`, e2e `test_zero_inputs` |
| M2.1 | Only shower, laundry, bathroom sink can enter | PASS in formula, catalog, prompt. FAIL in validation: "kitchen sink", "toilet and shower water", "blackwater" passed | ramadi.py:142 | 7ae6c3a | `test_no_kitchen_or_toilet_source_anywhere`, `test_banned_variants_rejected` |
| M2.2 | Laundry per household, showers per person | PASS | ramadi.py:55 | n/a | `test_laundry_is_per_household_showers_per_person` |
| M2.3 | Weekly → yearly conversion (no × 4) | PASS (× 52; no monthly greywater figure exists) | ramadi.py:77 | n/a (named constant in d337760) | `test_greywater_annual_is_52_weeks` |
| M2.4 | Greywater counted toward tanker trips | UNCLEAR: counted at `tanker_share`; the CSV does not say so | ramadi.py:83 | n/a (decision 2) | n/a |
| M3.1 | Trips = water × tanker_share ÷ volume; rounding consistent | PASS. Fractional everywhere, never floored; shown to 1 dp (header, Sareef) and 0 dp (community total) | ramadi.py:63 | n/a | `test_impact_formulas`, `test_trips_are_fractional_not_floored` |
| M3.2 | JOD and CO₂ formulas, factors in CSV | PASS; meaning of the pump-energy term is UNCLEAR (decision 8) | ramadi.py:64–65 | n/a | `test_impact_formulas` |
| M3.3 | Payback "n/a" when savings ≤ 0, never an error | PASS in engine; FAIL in UI (a valid 0-month payback showed "n/a") | app.py:75 | afa1bb2 | `test_payback_na_when_nothing_saved`, `test_zero_cost_payback_is_zero_months_not_na`, e2e `test_zero_inputs` |
| M3.4 | Payback before generation uses template cost | PASS | app.py:61 | n/a | `test_pre_generation_payback_uses_template_cost`, e2e `test_happy_path` |
| M4 | Sareef deltas signed and consistent | PASS, but logic sat in app.py | app.py:103–111 | afa1bb2 | `test_sareef_signs_and_consistency`, e2e `test_sareef_toggle_signs` |
| S2 | Community slider linear 1–1,000 | PASS, logic sat in app.py | app.py:114 | afa1bb2 | `test_community_scales_linearly`, e2e `test_community_slider` |
| M5.1 | Schema forbids extra fields | FAIL: extra fields silently dropped | ramadi.py:103 | a6ed516 | `test_schema_mismatch`, `test_extra_top_level_field_rejected` |
| M5.2 | Same JSON schema sent as Ollama `format` | PASS | ramadi.py:255 | n/a | `test_chat_sends_schema_seed_and_returns_content` |
| M6.1 | Reject unknown item (own code) | PASS, but merged with out-of-budget | ramadi.py:156 | 7ae6c3a | `test_unknown_item` |
| M6.2 | Reject single item outside the budget level | PASS, merged as above | ramadi.py:156 | 7ae6c3a | `test_item_over_budget` |
| M6.3 | Reject total BOM over budget | FAIL: no such check. No JOD budget exists anywhere, so a cap can't be set without inventing one | n/a | 7ae6c3a (check exists, inactive until a cap row is added) | `test_bom_over_budget`, `test_bom_cap_counts_required_items`, e2e `test_fallback_over_budget_total` |
| M6.4 | Quantity integer 1–50 | FAIL: `"5"`, `5.0` and `true` accepted | ramadi.py:94 | a6ed516 | `test_bad_quantity`, `test_quantity_bounds_accepted` |
| M6.5 | Plant not greywater-safe | PASS; unknown and unsafe plants were one message | ramadi.py:160 | 7ae6c3a | `test_every_raw_eaten_plant_rejected`, `test_unknown_plant` |
| M6.6 | Banned terms: case, Arabic normalisation, word boundaries | FAIL: no normalisation, so `لِلشُّرْبِ`, `لـلـشـرب`, presentation forms, zero-width characters, `chlorinated` and line-broken phrases passed. Word boundaries deliberately not applied (§2.6) | ramadi.py:161–165 | 7ae6c3a, b323b90 | `test_every_banned_term_in_every_field`, `test_banned_variants_rejected`, `test_alef_forms_normalise`, `test_allowed_phrases_not_rejected` |
| M7.1 | Strip `<think>` and code fences before parsing | FAIL | ramadi.py:150 | 7ae6c3a | `test_think_and_fence_stripped`, `test_unclosed_think_rejected` |
| M7.2 | Retry count in one constant | Code made 3 calls via `retries=2` argument; PRD is ambiguous (§2.1) | ramadi.py:284 | 80590c3 (`MAX_ATTEMPTS = 3`) | `test_retry_constant_is_three_attempts`, `test_failures_fall_back_to_template` |
| M7.3 | Every failure ends in template + notice, nothing uncaught | PARTIAL: always fell back, but the notice blamed "validation" for a dead server, and a dead or slow server was called 3 times (up to 9 min) | ramadi.py:289–299, app.py:131 | 80590c3, afa1bb2 | `test_failures_fall_back_to_template` (12 failure types), e2e `test_fallback_paths`, `test_ollama_not_installed` |
| M7.4 | Explicit timeout; temperature and seed | FAIL: no seed (timeout 180 s, temperature 0.3 were present) | ramadi.py:256 | 80590c3 | `test_chat_sends_schema_seed_and_returns_content`, `test_chat_timeout` |
| M8 | First flush and labels injected once | PASS; FAIL: injected reason was English in Arabic plans | ramadi.py:174 | 59f0604 | `test_required_items_added_once_in_plan_language`, `test_required_items_not_duplicated` |
| M9 | Warnings and disclaimer in the download, in plan language, Arabic RTL | PASS for text; FAIL: no RTL markup in the `.md` | ramadi.py:316 | 59f0604 | `test_markdown_has_warnings_disclaimer_and_direction`, e2e `test_arabic_plan_and_download` |
| M9.x | Template plan passes the validator | PASS | n/a | n/a | `test_template_passes_validator` (hypothesis, both budgets × both languages), `test_template_passes_own_validation` |
| SEC | Model text rendered with `unsafe_allow_html` unescaped | FAIL: model could inject HTML | app.py:140–158 | afa1bb2 | e2e `test_model_html_is_escaped` |
| M11.1 | Every constant in a CSV with source and status, shown in app | FAIL: 4 tables had no status column (plants had no source); monthly shares not shown in the app | data/*.csv, app.py:192 | f81d52f, ef729f4 | `test_every_table_has_source_and_status`, `test_every_assumption_used_in_code_is_in_csv`, e2e `test_assumptions_tab_lists_every_constant` |
| M11.2 | Loaders check columns and types, clear errors | FAIL | ramadi.py:20–30 | 6a36d59 | `test_loader_fails_loudly` (15 cases), `test_missing_file_is_data_error` |
| M12 | No network except local Ollama; runs without Ollama | PASS | n/a | n/a | e2e `test_external_sockets_blocked`, `test_ollama_not_installed`, `test_chat_when_ollama_not_running`; `pytest.ini` blocks non-local sockets for every test |

Python numbers that aren't in a CSV, kept on purpose:
- **Calendar/unit facts:** `DAYS_IN_MONTH`, `WEEKS_PER_YEAR = 52`, `LITRES_PER_M3`, `MM_PER_M`, `KG_PER_TONNE`, 12 months in payback.
- **Spec rules:** `QTY_MIN/QTY_MAX` 1–50 (M6), `REASON_MAX` 200, `COMMUNITY_MAX_HOMES` 1000 (S2), `MAX_ATTEMPTS` 3 (M7).
- **Config:** `OLLAMA_URL`, timeouts 2 s and 180 s, temperature 0.3, seed 42.
- **Not data, but they affect the numbers. Your call:** the template plan's quantities (gutter clamp(round(2√roof), 4, 50) m; leaf screens 2, downpipes 2, pipe 3, mulch basins 2) and its tank choice (1 m³ low, 2 m³ full). These set the pre-generation payback (PRD §8). The UI slider ranges and the "24 hours" in `WARNINGS` are also unsourced.

## 2. Spec conflicts and decisions for you

1. **Retry count.** M7 and README say "two retries" (3 calls); §4 says "fails twice" (2 calls). Code keeps 3 (`MAX_ATTEMPTS`). I also changed one behaviour: a dead server, missing model or timeout now stops after 1 call, because retrying can't help and a timeout already costs 180 s. Output problems still get all 3.
2. **Greywater toward tanker trips.** `water = rain_used + greywater`, so greywater to trees counts toward trips and JOD at `tanker_share` (0.5). That's only right if the trees were already watered with bought water. For new trees it overstates savings. `assumptions.csv` doesn't say. Options: (a) keep and add a sentence to the `tanker_share` source; (b) add a separate share for garden water; (c) exclude greywater from trips/JOD.
3. **Rounding.** Trips stay fractional (an expected value, not a count), shown to 1 dp; the community line uses 0 dp. If you'd rather show whole trips, decide floor vs round, since it changes JOD.
4. **Total-BOM budget cap.** Neither the PRD nor the data defines a JOD budget; "budget" is a level (low/full). The check is in place and turns on if you add `budget_cap_low_jod` / `budget_cap_full_jod` rows to `assumptions.csv`. Otherwise, drop the requirement.
5. **Who owns quantity limits.** PRD §6 says `catalog.csv` does; M6 and the code use a global 1–50, and the catalog has no limit column. Not changed.
6. **Word-boundary matching.** Not done. Arabic attaches prefixes and suffixes (`للشرب`, `يشرب`) and English forms compounds (`undrinkable`), so whole-word matching would let real mentions through. Substring matching on normalised text is kept, with a short allow-list (`toilet cistern`, `flush toilet`, `طرد المراحيض`, …). Known false rejections: `تشرب` (soil absorbs), `مشربية`, `unbleached`, `kitchen garden`, any `toilet` outside the allow-list. These cost a retry, which PRD §6 accepts.
7. **Banned list was tightened, not loosened:** added `chemical` (PRD §6 names it), `chlorin`, `clorox`, `kitchen`, `toilet`, `dishwasher`, `blackwater`, and Arabic `مرحاض/مراحيض/تواليت/مطبخ/مجلى/جلاية/كيميا/مياه سوداء/مياه الصرف الصحي`. The Arabic terms and the new Arabic note `مطلوب حسب قواعد السلامة.` need native review (M10).
8. **Pump-energy CO₂ term.** `impact` adds `water × pump_energy × grid_co2` to "CO₂ cut" for all water, including the tanker share and gravity-fed greywater. Is this the grid energy of municipal supply saved, or the system's own pump? If it's the system's pump, the sign is wrong.
9. **dry < average < wet** is strict only for roof inflow. Rain actually used saturates once demand is met or the tank is full, so equality is correct there. M1's acceptance line reads as strict for everything.
10. **Template tank ignores the sidebar tank size.** A user choosing 8 m³ gets a 1 or 2 m³ tank priced in payback.
11. **UI change:** the people slider now starts at 0, so zero occupancy can be tested end to end. Revert if unwanted.
12. **Speed.** One real run with `llama3.2:3b` here took about 170 s per plan (both languages accepted first time) against the §7 target of under 30 s. `CHAT_TIMEOUT_S = 180` has almost no headroom on this laptop.

## 3. Data values to source first (PRD §9 order)

Values are unchanged. These look weakest:

1. **Tanker.** `tanker_share` 0.5 is a pure guess and scales trips, JOD and CO₂ linearly: the biggest single lever. `tanker_volume` 5 m³ and `diesel_per_trip` 4 L are unsourced (4 L implies a short round trip). `municipal_tariff` 1.0 JOD/m³ looks high for typical residential blocks; check it against the published tariff table.
2. **Rain.** One national monthly profile applies to every governorate (Aqaba gets Irbid's season shape). Amman (west) 450 mm and Salt 550 mm are at the high end. `first_flush_loss` is modelled as 10% of all rain, but real diverters drop a fixed volume per storm, so this overstates loss in big storms and understates it in many small ones.
3. **Demand.** `nonpotable_litres_per_person_day` 30 L is unsourced; cleaning on top of flushing may push it higher.
4. **Catalog.** `transfer_pump` 60 JOD looks low. All prices are placeholders.
5. **Greywater rules.** The 24-hour storage window in `WARNINGS` is unsourced. In `plants.csv`, rosemary is marked greywater-safe although it's commonly eaten; safety relies on the note "hedge only". Plant sources were never recorded.

## 4. Not tested, and why

- **Arabic quality (M10):** needs a native speaker; tests only check that the right text and RTL markup are present.
- **Visual rendering:** RTL CSS, charts and badge appearance. The optional Playwright smoke test was skipped to avoid adding a browser dependency; AppTest checks element content, not layout.
- **Download bytes:** e2e tests spy on `ramadi.to_markdown`, which feeds the button. They don't read the file Streamlit serves, because AppTest keeps it in internal media storage.
- **Real model behaviour and latency:** CI uses fakes and a local fake HTTP server. Only one manual run against a real model (above).
- **Model selector (S1) with several installed models,** and stale-plan clearing when inputs change: not driven end to end.
- **`DataError` / `InputError` screens in the UI:** unit-tested in the engine, not via AppTest.
