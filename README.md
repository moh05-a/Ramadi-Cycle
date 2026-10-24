# CARE — Clinical Assessment & Risk Engine (hackathon MVP)

Simulated ED operations assistant. **Fictional data only — not for clinical use.**

- Product: [docs/PRD.md](docs/PRD.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Run

```sh
# terminal 1 — API on :8080
cd backend && go run .

# terminal 2 — UI on :5173 (proxies /api to :8080)
cd frontend && npm install && npm run dev
```

Tests: `cd backend && go test ./...`
