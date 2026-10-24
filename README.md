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

## Test

```bash
pytest -q
```

## How it works

Python calculates every number, price and safety rule. The local model only picks parts from `data/catalog.csv` and writes the steps. Its JSON is validated against a schema; unknown parts, raw-eaten plants, bad quantities or banned terms get it rejected. After two failed retries the app shows the template plan and says so.

| File | What's in it |
| --- | --- |
| `ramadi.py` | Water-balance engine, schema, safety rules, Ollama call, template plan |
| `app.py` | Streamlit interface |
| `data/*.csv` | Rainfall, monthly shares, catalog, plants, assumptions. Every constant lives here |
| `PRD.md` | Product requirements |
| `BRAND.md` | Name, mark, colour, type, voice |
| `docs/` | Original project documentation |

## Limits

Every constant in `data/` is a placeholder or unverified, and the app says so. Results are general guidance, not an approved plumbing design or legal advice. Check Jordanian rules on greywater reuse and hire a licensed plumber.

## License

MIT
