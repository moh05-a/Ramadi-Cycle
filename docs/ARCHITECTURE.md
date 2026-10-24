# CARE — Architecture (MVP)

```
┌──────────────────────────┐   /api (Vite proxy)   ┌──────────────────────────────┐
│ frontend/  React + Vite  │ ───────────────────▶  │ backend/  Go net/http :8080  │
│ TS + Tailwind + Recharts │ ◀── JSON dashboard ── │ in-memory State + mutex      │
└──────────────────────────┘                       └──────────────────────────────┘
```

The original concept doc proposes Python/FastAPI + SQLite. This MVP uses **Go (stdlib only)** and an
**in-memory store**: no DB setup, and Reset already gives the reproducible state a demo needs.

## Backend (`backend/`)

| File | Responsibility |
|---|---|
| `main.go` | HTTP routes, JSON encode/decode, request validation |
| `state.go` | Data model, seed data, simulated clock, scenarios, human review, dashboard view |
| `rules.go` | Pure `checkRules(state) []Alert` + merge into existing alerts |
| `rules_test.go` | Scenario → expected alert tests |

### Data flow

```
scenario / review request
   → mutate State (patients, tasks, beds, lab turnaround, clock)
   → checkRules()  (deterministic, versioned "rules-v0.1")
   → merge alerts  (stable IDs keep human review status)
   → append DepartmentSnapshot (trend chart)
   → return full dashboard JSON
```

- **Simulated clock**: `State.Now` starts at 2026-10-24 14:00 UTC and only moves when a scenario runs. Tests are deterministic.
- **Alert IDs** are derived from rule + subject (e.g. `overdue_task:T2`), so re-evaluating doesn't duplicate alerts or lose review status.
- Open alerts whose condition clears become `resolved`. Human-closed alerts stay closed.
- One global mutex guards state — fine for a single-room demo.

### Data model

| Entity | Fields |
|---|---|
| Patient | id, alias, ageBand, area, status (`waiting`/`in_bed`), arrivedAt, lastReassessedAt, pendingTest |
| Task | id, caseId, type, owner, dueAt, status (`open`/`done`) |
| Alert | id, rule, ruleVersion, severity, title, evidence{}, uncertainty, suggestion, caseId, taskId, createdAt, status |
| AuditEvent | id, at, alertId, reviewerRole, decision, reason, alert (snapshot) |
| Snapshot | at, waiting, bedsAvailable, pendingTasks, labTurnaroundMin |

### API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/dashboard` | – | Dashboard |
| POST | `/api/scenarios/{id}/run` | – (`reset`, `stable`, `surge`, `lab_delay`, `bed_block`) | Dashboard |
| POST | `/api/alerts/{id}/review` | `{decision, reason, reviewerRole}` | Dashboard |
| GET | `/api/audit` | – | AuditEvent[] |

Mutations return the full dashboard so the UI has one source of truth and no client-side state sync.

## Frontend (`frontend/`)

- `src/api.ts` — types mirroring backend JSON + fetch helpers.
- `src/App.tsx` — single dashboard page, layout from the concept doc:
  - top: metric tiles · left: patient queue · center: alert feed · right: action queue · bottom: trend chart + audit trail
  - header: demo controls + permanent **SIMULATED — NOT FOR CLINICAL USE** banner.
- Vite dev server proxies `/api` → `localhost:8080`, so no CORS.

## Not in MVP (upgrade path)

| Gap | Upgrade when |
|---|---|
| In-memory state (lost on restart) | Need persistence across restarts → SQLite via `modernc.org/sqlite` |
| No auth / reviewer role is free text | Any non-demo use |
| Polling-free (refresh on action) | Multiple screens need live sync → poll or SSE |
| No LLM layer | Stretch: note parsing with schema validation + fallback |
