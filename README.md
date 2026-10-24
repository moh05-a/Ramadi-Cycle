# Ramadi-Cycle (رمادي)

<img src="assets/logo.svg" width="260" alt="Ramadi-Cycle">

Shows a Jordanian household how much water, money and diesel it can save with rainwater harvesting and greywater reuse, then produces a priced, safety-checked build plan in English or Arabic. Runs entirely on one laptop. No cloud, no accounts, no personal data.

Built for JOSA Hacktoberfest '26, Track 1: Green Tech & Earth Preservation.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app works without a model: blueprints fall back to a built-in template. For generated plans, install [Ollama](https://ollama.com) and pull a small open-weight model:

```bash
ollama pull qwen3:4b      # or gemma3:4b, llama3.2:3b, any model Ollama serves
```

Installed models appear in the sidebar. Switch between them freely.

### Web interface (React)

A second interface built from the brand kit. It gets every number, plan line and warning from `ramadi.py` through a small local API.

```bash
python api.py                         # terminal 1: API on 127.0.0.1:8000
cd frontend && npm install && npm run dev   # terminal 2: http://localhost:5173
```

## Test

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests never touch a real model or the network: Ollama is replaced by fakes, and any socket to a host other than this machine fails the run.

## How it works

Python calculates every number, price and safety rule. The local model only picks parts from `data/catalog.csv` and writes the steps. Its JSON is validated against a schema; unknown parts, raw-eaten plants, bad quantities or banned terms get it rejected. After two failed retries the app shows the template plan and says so.

| File | What's in it |
| --- | --- |
| `ramadi.py` | Water-balance engine, schema, safety rules, Ollama call, template plan |
| `app.py` | Streamlit interface |
| `api.py` | Local JSON API over `ramadi.py` for the web interface. No logic of its own |
| `frontend/` | React web interface (v3 design), built on `brand-kit/` |
| `data/*.csv` | Rainfall, monthly shares, catalog, plants, assumptions. Every constant lives here |
| `scripts/fetch_climate.py` | Refreshes `data/sources/` from NASA POWER and NOAA GHCN-Daily (free, no key). Run by hand; the app stays offline |
| `PRD.md` | Product requirements |
| `BRAND.md` | Name, mark, colour, type, voice |
| `brand-kit/` | React tokens, components and style guide for the frontend team |
| `docs/` | Original project documentation |

## Limits

Rainfall comes from published station normals, and year-to-year variability and first-flush loss come from open weather data (see each row's `source`). Five governorate rainfall totals, the household water-use figures, tanker volume, tanker share, diesel per trip, catalog prices and plant safety notes are still estimates or placeholders, and the app says so. Results are general guidance, not an approved plumbing design or legal advice. Check Jordanian rules on greywater reuse and hire a licensed plumber.

## License

MIT
