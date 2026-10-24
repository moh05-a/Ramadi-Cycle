package main

import (
	"fmt"
	"time"
)

const (
	ruleVersion          = "rules-v0.1"
	reassessEvery        = 60 * time.Minute
	labDelayThresholdMin = 60
	queuePressureWaiting = 10
	deterministic        = "Deterministic rule on simulated data"
)

// checkRules is pure: same state in, same alerts out.
func checkRules(s *State) []Alert {
	var out []Alert
	add := func(a Alert) {
		a.RuleVersion = ruleVersion
		if a.Uncertainty == "" {
			a.Uncertainty = deterministic
		}
		out = append(out, a)
	}

	for _, p := range s.Patients {
		if p.Status == "waiting" {
			since := s.Now.Sub(p.LastReassessedAt)
			if since > reassessEvery {
				sev := "medium"
				if since > 90*time.Minute {
					sev = "high"
				}
				add(Alert{
					// timestamp in the ID so a new cycle after completion raises a fresh alert
					ID: fmt.Sprintf("overdue_reassessment:%s:%d", p.ID, p.LastReassessedAt.Unix()), Rule: "overdue_reassessment",
					Severity: sev, Title: "Reassessment overdue: " + p.Alias, CaseID: p.ID,
					Evidence:   map[string]any{"patient": p.Alias, "minutesSinceReassessment": int(since.Minutes()), "thresholdMin": int(reassessEvery.Minutes())},
					Suggestion: "Reassess " + p.Alias + " and record the time.",
				})
			}
		}
		var missing []string
		if p.Area == "" {
			missing = append(missing, "area")
		}
		if p.AgeBand == "" {
			missing = append(missing, "ageBand")
		}
		if len(missing) > 0 {
			add(Alert{
				ID: "missing_field:" + p.ID, Rule: "missing_field", Severity: "medium",
				Title: "Missing critical field: " + p.Alias, CaseID: p.ID,
				Evidence:    map[string]any{"patient": p.Alias, "missing": missing},
				Uncertainty: "Needs human review: required data missing",
				Suggestion:  "Complete the missing fields before relying on other alerts for this patient.",
			})
		}
	}

	for _, t := range s.Tasks {
		if t.Status == "open" && s.Now.After(t.DueAt) {
			add(Alert{
				ID: "overdue_task:" + t.ID, Rule: "overdue_task", Severity: "medium",
				Title: "Task overdue: " + t.Type, CaseID: t.CaseID, TaskID: t.ID,
				Evidence:   map[string]any{"task": t.Type, "owner": t.Owner, "minutesOverdue": int(s.Now.Sub(t.DueAt).Minutes())},
				Suggestion: "Confirm an owner and complete \"" + t.Type + "\".",
			})
		}
	}

	waiting, longest := s.waiting()
	if waiting >= queuePressureWaiting {
		arrivals := 0
		for _, p := range s.Patients {
			if s.Now.Sub(p.ArrivedAt) <= 30*time.Minute {
				arrivals++
			}
		}
		add(Alert{
			ID: "queue_pressure", Rule: "queue_pressure", Severity: "high", Title: "Rising queue pressure",
			Evidence:   map[string]any{"waiting": waiting, "threshold": queuePressureWaiting, "arrivalsLast30Min": arrivals, "longestWaitMin": longest},
			Suggestion: "Review bed turnover and assign owners to pending reassessments.",
		})
	}
	if s.LabTurnaroundMin > labDelayThresholdMin {
		add(Alert{
			ID: "lab_delay", Rule: "lab_delay", Severity: "medium", Title: "Lab turnaround delayed",
			Evidence:   map[string]any{"labTurnaroundMin": s.LabTurnaroundMin, "thresholdMin": labDelayThresholdMin},
			Suggestion: "Contact lab for ETA and prioritise results blocking disposition.",
		})
	}
	if s.BedsAvailable == 0 && waiting > 0 {
		add(Alert{
			ID: "bed_bottleneck", Rule: "bed_bottleneck", Severity: "high", Title: "Bed bottleneck",
			Evidence:   map[string]any{"bedsAvailable": 0, "bedsTotal": s.BedsTotal, "waiting": waiting},
			Suggestion: "Review discharges and inpatient transfers to free beds.",
		})
	}
	return out
}

// evaluate merges fresh rule output into s.Alerts, keeping review status by alert ID.
func (s *State) evaluate() {
	fired := map[string]bool{}
	for _, a := range checkRules(s) {
		fired[a.ID] = true
		old := s.alert(a.ID)
		switch {
		case old == nil:
			a.CreatedAt, a.Status = s.Now, "open"
			s.Alerts = append(s.Alerts, &a)
		case old.Status == "open" || old.Status == "acknowledged":
			old.Evidence, old.Severity = a.Evidence, a.Severity
		case old.Status == "resolved":
			old.Evidence, old.Severity, old.Status, old.CreatedAt = a.Evidence, a.Severity, "open", s.Now
		}
		// shortcut: a human-closed alert stays closed while its condition persists; add re-raise rules if demos need it
	}
	for _, a := range s.Alerts {
		if !fired[a.ID] && (a.Status == "open" || a.Status == "acknowledged") {
			a.Status = "resolved"
		}
	}
}
