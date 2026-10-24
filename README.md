# Ramadi-Cycle (رمادي)

<img src="assets/logo.svg" width="260" alt="Ramadi-Cycle">

Shows a Jordanian household what its greywater can grow. Tell it about your home and what you want from your garden, in Arabic or English, and a local AI model designs a garden that your shower, sink and laundry water, plus winter rain from the roof, can keep alive in every month, August included. Code checks every litre before you see the plan. Then it shows the tanker trips, dinars and CO₂ that water saves, and a priced build plan for the plumbing. Runs entirely on one laptop. No cloud, no accounts, no personal data.

Built for JOSA Hacktoberfest '26, Track 1: Green Tech & Earth Preservation.

## Run it

The garden planner is in the web interface. It gets every number, plant check and warning from `ramadi.py` through a small local API.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python api.py                                   # terminal 1: API on 127.0.0.1:8000
cd frontend && npm install && npm run dev       # terminal 2: http://localhost:5173
```

Garden suggestions need a model. Install [Ollama](https://ollama.com) and pull a small open-weight model:

```bash
ollama pull qwen3:4b      # or gemma3:4b, llama3.2:3b, any model Ollama serves
```

Installed models appear in the model picker. Switch between them freely. Without a model the water, soil, savings and build plan still work, but there are no plant suggestions: plants only ever come from the model, after code has checked them.

### Streamlit interface

The first interface, kept for the savings numbers and the build plan. It has no garden planner.

```bash
streamlit run app.py
```

### Optional: cloud models through OpenRouter

Off by default, so the app stays fully offline. To also offer open-weight models hosted on OpenRouter, set a key in the environment before starting the API or the app. Never put the key in a file in this repo.

```bash
export OPENROUTER_API_KEY=sk-or-...           # your key
export OPENROUTER_MODELS=liquid/lfm-2.5-2.6b:free,google/gemma-4-26b-a4b-it:free   # optional; defaults in ramadi.py
python api.py                                  # or: streamlit run app.py
```

Cloud models appear in the model picker marked as cloud. Choosing one sends the household numbers, the garden wishes and the prompt to OpenRouter, and the app says so on screen. The same checks and retries apply. A free-tier key only works with `:free` models, which are often busy upstream.

## Test

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests never touch a real model or the network: Ollama is replaced by fakes, and any socket to a host other than this machine fails the run.

## How it works

**1. Your water.** Python works out, month by month, how much greywater the household makes (showers, bathroom sinks, laundry; never toilet or kitchen water) and how much rain the roof tank collects. Greywater goes to the garden every day; the rain tank serves toilet flushing and cleaning, and its winter overflow goes to the garden too.

**2. Your garden (the AI part).** A local model reads what the family wants, for example "fruit for the kids and shade by the wall", and picks plants and counts from `data/garden_plants.csv`. It sees a short prompt: each plant's size and summer water need for this governorate, the garden's water budget, the soil and the air humidity. Code then works out what each plant needs in every month (FAO-56: ET₀ × Kc × canopy, less effective rain, over drip efficiency) and rejects any garden that runs dry in a month, doesn't fit the space, uses a plant that can't take greywater, or contains banned words. The reason goes back to the model so it can fix the plan, up to three attempts. If none passes, the app says so and shows no plants: it never invents a garden.

**3. What it saves.** The water the system supplies becomes tanker trips avoided, dinars saved, kg of CO₂ cut and a payback time, with a before/after toggle and a neighbourhood scale-up.

**4. How to build it.** A priced, safety-checked parts list and build steps for the gutters, first-flush diverter, tank, greywater valve, filter and drip line, written by the model or by a fixed template. A first-flush diverter and outlet labels are always added by code.

Python owns every number, price and safety rule. The model only picks plants and parts from fixed tables and writes the words.

| File | What's in it |
| --- | --- |
| `ramadi.py` | Water engine, garden planner, schemas, safety rules, model calls, build-plan template |
| `api.py` | Local JSON API over `ramadi.py` for the web interface. No logic of its own |
| `frontend/` | React web interface with the garden planner, built on `brand-kit/` |
| `app.py` | Streamlit interface (savings and build plan) |
| `data/*.csv` | Every constant: rainfall, monthly shares, evaporation, humidity, soil, plant water needs, catalog, assumptions |
| `scripts/fetch_climate.py` | Refreshes the climate and soil tables from NASA POWER, NOAA GHCN-Daily and ISRIC SoilGrids (free, no key). Run by hand; the app stays offline |
| `PRD.md` | Product requirements |
| `BRAND.md` | Name, mark, colour, type, voice |
| `brand-kit/` | React tokens, components and style guide for the frontend team |
| `docs/` | Project documentation |

## Data

Monthly evaporation (ET₀) and air humidity per governorate come from NASA POWER daily weather, 1991-2020, with ET₀ by FAO-56 Penman-Monteith. Soil texture and pH come from ISRIC SoilGrids (the nearest mapped point where the town centre is built up). Plant crop factors come from FAO-56 and salt tolerance from FAO-29 where those list the plant. Rainfall comes from published station normals; year-to-year variability and first-flush loss from open weather data. Every row carries a `source` and a `status`.

## Limits

Fig and pomegranate crop factors, mature plant sizes, five governorate rainfall totals, the household water-use figures, tanker volume and share, diesel per trip and catalog prices are still estimates or placeholders, and the app says so. Garden water needs are for plants at full size. Results are general guidance, not an approved plumbing design, an agronomy survey or legal advice. Check Jordanian rules on greywater reuse and hire a licensed plumber.

## License

MIT
