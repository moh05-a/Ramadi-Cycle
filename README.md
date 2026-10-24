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

### Optional: cloud models through OpenRouter

Off by default, so the app stays fully offline. To also offer open-weight models hosted on OpenRouter, set a key in the environment before starting the app or the API. Never put the key in a file in this repo.

```bash
export OPENROUTER_API_KEY=sk-or-...           # your key
export OPENROUTER_MODELS=liquid/lfm-2.5-2.6b:free,google/gemma-4-26b-a4b-it:free   # optional; defaults in ramadi.py
streamlit run app.py                           # or: python api.py
```

Cloud models appear in the model picker marked as cloud. Choosing one sends the household numbers and the prompt to OpenRouter, and the app says so on screen. The same validation, retries and template fallback apply. A free-tier key only works with `:free` models, which are often busy upstream.

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
| `PRD.md` | Product requirements |
| `BRAND.md` | Name, mark, colour, type, voice |
| `brand-kit/` | React tokens, components and style guide for the frontend team |
| `docs/` | Original project documentation |

## Limits

Every constant in `data/` is a placeholder or unverified, and the app says so. Results are general guidance, not an approved plumbing design or legal advice. Check Jordanian rules on greywater reuse and hire a licensed plumber.

## License

MIT
