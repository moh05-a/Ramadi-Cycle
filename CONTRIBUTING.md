# Contributing

The most useful contributions are better numbers. Every constant lives in `data/`, and every row has a `source` column.

## Good first issues

1. Replace a governorate's rainfall in `data/rainfall.csv` with a cited station value.
2. Replace the placeholder monthly shares in `data/monthly_share.csv` with station data.
3. Add or correct a catalog item in `data/catalog.csv` with a local price and the shop as source.
4. Add a drought-tolerant plant to `data/plants.csv` with a greywater note.
5. Review the Arabic in the warnings and template plan in `ramadi.py`.

## Rules

- A changed number needs a source in the same row. Set `status` in `assumptions.csv` to `verified` only with a primary source.
- Don't add catalog parts that divert toilet or kitchen water.
- Don't loosen `BANNED_TERMS`, `WARNINGS` or `REQUIRED_ITEMS` without an issue explaining why.
- Run `pytest -q` before opening a pull request.
