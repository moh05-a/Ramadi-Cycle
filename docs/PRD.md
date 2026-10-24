# CARE — Product Requirements (MVP)

**CARE (Clinical Assessment & Risk Engine)** is a clinician-in-the-loop ED operations assistant.
It turns patient and department signals into explainable alerts and suggested next steps.
**Simulated data only. Not for clinical use.**

## 1. Problem

| Problem | What it looks like on shift |
|---|---|
| Fragmented awareness | Waiting patients, pending tests, beds and staffing live in different places |
| Missed follow-ups | Reassessments and test reviews slip when the ED is busy |
| Late strain detection | Rising arrivals, lab delays and bed blocks are noticed too late |
| Opaque alerts | Staff ignore warnings they can't see the reason for |

## 2. Users

- **Charge nurse** (primary): watches department pressure, assigns follow-ups, reviews alerts.
- **ED clinician**: acknowledges/completes patient-level alerts.
- **Hackathon judge**: watches a 2–3 minute scripted demo.

## 3. Goals / Non-goals

**Goals**
- One screen showing patients, department pressure, alerts, tasks and audit trail.
- Every alert shows the rule, measured value, threshold, time window and suggestion.
- Every human decision is recorded with a reason when it overrides/dismisses.
- Deterministic, reproducible demo scenarios.

**Non-goals**
- Diagnosis, triage decisions, orders, or changing care automatically.
- Real patient data, hospital integrations, auth, production deployment.
- LLM features in the MVP (note parsing / explanation drafting are stretch).

## 4. MVP scope

| # | Feature | Acceptance criteria |
|---|---|---|
| F1 | Live ED board | Patient cards show alias, age band, area, status, wait time, pending test, last reassessment |
| F2 | Operational overview | Active patients, waiting, longest wait, pending tasks, beds available, lab turnaround, trend chart |
| F3 | Rule-based alerts | Overdue reassessment, missing critical field, overdue task, queue pressure, lab delay, bed bottleneck |
| F4 | Explainable alert cards | Severity, rule + version, evidence values, threshold, timestamp, uncertainty, suggestion |
| F5 | Action queue | Tasks with owner, due time, status |
| F6 | Human review | Acknowledge / complete / dismiss / override; dismiss & override require a reason |
| F7 | Audit log | Timestamp, reviewer role, decision, reason, alert snapshot |
| F8 | Demo controls | Reset, Stable Shift, Surge, Lab Delay, Bed Block |

**Stretch (not built):** SPC charts, tabular prediction model + SHAP, Arabic/English note summarization, what-if simulator, staffing-shortage scenario, free-form event entry.

## 5. Alert rules (v0.1)

| Rule | Fires when | Severity |
|---|---|---|
| `overdue_reassessment` | Waiting patient not reassessed for > 60 min | medium (> 90 min: high) |
| `missing_field` | Patient missing area or age band | medium, "Needs human review" |
| `overdue_task` | Open task past its due time | medium |
| `queue_pressure` | Waiting count ≥ 10 | high |
| `lab_delay` | Lab turnaround > 60 min | medium |
| `bed_bottleneck` | 0 beds available and ≥ 1 patient waiting | high |

## 6. Demo script

1. **Reset** → 8 fictional patients, 2 free beds, 2 baseline alerts (overdue reassessment, missing field).
2. **Stable Shift** → 1 arrival, clock +15 min, a seeded task goes overdue.
3. **Surge** → 6 arrivals over 30 min, lab turnaround 75 min → queue-pressure + lab-delay alerts.
4. **Bed Block** → beds hit 0 → bed-bottleneck alert.
5. Reviewer **completes** a reassessment, **overrides** queue pressure with a reason → both appear in audit log, metrics update.

## 7. Success criteria

- Every scenario produces its expected alert (Go unit tests).
- Reset always returns the same state.
- Override/dismiss without a reason is rejected.
- UI labels the environment as **SIMULATED** at all times.

## 8. Safety

Advisory only. Fictional data only. Rules are deterministic and versioned; no model downgrades an alert.
Incomplete data shows "Needs human review" instead of a confident answer.
