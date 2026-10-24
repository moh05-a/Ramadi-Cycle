package main

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"
)

type Patient struct {
	ID               string    `json:"id"`
	Alias            string    `json:"alias"`
	AgeBand          string    `json:"ageBand"`
	Area             string    `json:"area"`
	Status           string    `json:"status"` // waiting | in_bed
	ArrivedAt        time.Time `json:"arrivedAt"`
	LastReassessedAt time.Time `json:"lastReassessedAt"`
	PendingTest      string    `json:"pendingTest,omitempty"`
}

type Task struct {
	ID     string    `json:"id"`
	CaseID string    `json:"caseId"`
	Type   string    `json:"type"`
	Owner  string    `json:"owner"`
	DueAt  time.Time `json:"dueAt"`
	Status string    `json:"status"` // open | done
}

type Alert struct {
	ID          string         `json:"id"`
	Rule        string         `json:"rule"`
	RuleVersion string         `json:"ruleVersion"`
	Severity    string         `json:"severity"` // high | medium | low
	Title       string         `json:"title"`
	Evidence    map[string]any `json:"evidence"`
	Uncertainty string         `json:"uncertainty"`
	Suggestion  string         `json:"suggestion"`
	CaseID      string         `json:"caseId,omitempty"`
	TaskID      string         `json:"taskId,omitempty"`
	CreatedAt   time.Time      `json:"createdAt"`
	Status      string         `json:"status"` // open | acknowledged | completed | dismissed | overridden | resolved
}

type AuditEvent struct {
	ID           int       `json:"id"`
	At           time.Time `json:"at"`
	AlertID      string    `json:"alertId"`
	ReviewerRole string    `json:"reviewerRole"`
	Decision     string    `json:"decision"`
	Reason       string    `json:"reason"`
	Alert        Alert     `json:"alert"`
}

type Snapshot struct {
	At               time.Time `json:"at"`
	Waiting          int       `json:"waiting"`
	BedsAvailable    int       `json:"bedsAvailable"`
	PendingTasks     int       `json:"pendingTasks"`
	LabTurnaroundMin int       `json:"labTurnaroundMin"`
}

type State struct {
	Now              time.Time
	Patients         []*Patient
	Tasks            []*Task
	BedsTotal        int
	BedsAvailable    int
	LabTurnaroundMin int
	Alerts           []*Alert
	Audit            []AuditEvent
	History          []Snapshot
	nextPatient      int
}

var errNotFound = errors.New("not found")

func newState() *State {
	s := &State{}
	s.reset()
	return s
}

func (s *State) reset() {
	t0 := time.Date(2026, 10, 24, 14, 0, 0, 0, time.UTC)
	ago := func(m int) time.Time { return t0.Add(-time.Duration(m) * time.Minute) }
	*s = State{
		Now:              t0,
		BedsTotal:        12,
		BedsAvailable:    2,
		LabTurnaroundMin: 35,
		nextPatient:      8,
		Patients: []*Patient{
			{ID: "P1", Alias: "Amber Fox", AgeBand: "30-39", Area: "Resus", Status: "in_bed", ArrivedAt: ago(140), LastReassessedAt: ago(20)},
			{ID: "P2", Alias: "Birch Owl", AgeBand: "60-69", Area: "Majors", Status: "in_bed", ArrivedAt: ago(95), LastReassessedAt: ago(30), PendingTest: "Troponin"},
			{ID: "P3", Alias: "Cedar Lynx", AgeBand: "70-79", Area: "Waiting room", Status: "waiting", ArrivedAt: ago(110), LastReassessedAt: ago(70)},
			{ID: "P4", Alias: "Dune Heron", AgeBand: "20-29", Area: "Waiting room", Status: "waiting", ArrivedAt: ago(45), LastReassessedAt: ago(15)},
			{ID: "P5", Alias: "Elm Badger", AgeBand: "40-49", Area: "Minors", Status: "in_bed", ArrivedAt: ago(60), LastReassessedAt: ago(10), PendingTest: "X-ray"},
			{ID: "P6", Alias: "Fern Otter", AgeBand: "50-59", Area: "Waiting room", Status: "waiting", ArrivedAt: ago(35), LastReassessedAt: ago(25), PendingTest: "CBC"},
			{ID: "P7", Alias: "Glen Wren", AgeBand: "80+", Area: "", Status: "waiting", ArrivedAt: ago(20), LastReassessedAt: ago(20)},
			{ID: "P8", Alias: "Hazel Crow", AgeBand: "10-19", Area: "Waiting room", Status: "waiting", ArrivedAt: ago(10), LastReassessedAt: ago(10)},
		},
		Tasks: []*Task{
			{ID: "T1", CaseID: "P2", Type: "Review troponin result", Owner: "Dr. Demo A", DueAt: t0.Add(10 * time.Minute), Status: "open"},
			{ID: "T2", CaseID: "P6", Type: "Review CBC result", Owner: "unassigned", DueAt: t0.Add(25 * time.Minute), Status: "open"},
			{ID: "T3", CaseID: "P5", Type: "Review X-ray", Owner: "Dr. Demo B", DueAt: t0.Add(40 * time.Minute), Status: "open"},
		},
	}
	s.evaluate()
	s.snapshot()
}

func (s *State) addArrival() {
	s.nextPatient++
	id := fmt.Sprintf("P%d", s.nextPatient)
	s.Patients = append(s.Patients, &Patient{
		ID: id, Alias: fmt.Sprintf("Arrival %d", s.nextPatient), AgeBand: "unknown", Area: "Triage",
		Status: "waiting", ArrivedAt: s.Now, LastReassessedAt: s.Now,
	})
	s.Tasks = append(s.Tasks, &Task{
		ID: fmt.Sprintf("T%d", len(s.Tasks)+1), CaseID: id, Type: "Initial assessment",
		Owner: "unassigned", DueAt: s.Now.Add(30 * time.Minute), Status: "open",
	})
}

func (s *State) advance(d time.Duration) {
	s.Now = s.Now.Add(d)
	s.evaluate()
	s.snapshot()
}

func (s *State) runScenario(id string) error {
	switch id {
	case "reset":
		s.reset()
	case "stable":
		s.addArrival()
		s.advance(15 * time.Minute)
	case "surge":
		s.LabTurnaroundMin = 75
		for range 6 {
			s.addArrival()
			s.advance(5 * time.Minute)
		}
	case "lab_delay":
		s.LabTurnaroundMin = 95
		s.advance(20 * time.Minute)
	case "bed_block":
		s.BedsAvailable = 0
		s.advance(10 * time.Minute)
	default:
		return errNotFound
	}
	return nil
}

type ReviewRequest struct {
	Decision     string `json:"decision"`
	Reason       string `json:"reason"`
	ReviewerRole string `json:"reviewerRole"`
}

var decisionStatus = map[string]string{
	"acknowledge": "acknowledged",
	"complete":    "completed",
	"dismiss":     "dismissed",
	"override":    "overridden",
}

func (s *State) review(alertID string, req ReviewRequest) error {
	a := s.alert(alertID)
	if a == nil {
		return errNotFound
	}
	status, ok := decisionStatus[req.Decision]
	if !ok {
		return errors.New("decision must be acknowledge, complete, dismiss or override")
	}
	req.Reason = strings.TrimSpace(req.Reason)
	req.ReviewerRole = strings.TrimSpace(req.ReviewerRole)
	if (req.Decision == "dismiss" || req.Decision == "override") && req.Reason == "" {
		return errors.New("reason is required to dismiss or override")
	}
	if req.ReviewerRole == "" {
		return errors.New("reviewerRole is required")
	}
	if a.Status != "open" && a.Status != "acknowledged" {
		return fmt.Errorf("alert is already %s", a.Status)
	}

	a.Status = status
	if req.Decision == "complete" {
		for _, t := range s.Tasks {
			if t.ID == a.TaskID {
				t.Status = "done"
			}
		}
		if a.Rule == "overdue_reassessment" {
			for _, p := range s.Patients {
				if p.ID == a.CaseID {
					p.LastReassessedAt = s.Now
				}
			}
		}
	}
	s.Audit = append(s.Audit, AuditEvent{
		ID: len(s.Audit) + 1, At: s.Now, AlertID: a.ID, ReviewerRole: req.ReviewerRole,
		Decision: req.Decision, Reason: req.Reason, Alert: *a,
	})
	s.evaluate()
	s.History[len(s.History)-1] = s.snapshotNow() // keep the chart's last point in sync after a review
	return nil
}

func (s *State) alert(id string) *Alert {
	for _, a := range s.Alerts {
		if a.ID == id {
			return a
		}
	}
	return nil
}

func (s *State) waiting() (n int, longestMin int) {
	for _, p := range s.Patients {
		if p.Status == "waiting" {
			n++
			longestMin = max(longestMin, int(s.Now.Sub(p.ArrivedAt).Minutes()))
		}
	}
	return
}

func (s *State) openTasks() (n int) {
	for _, t := range s.Tasks {
		if t.Status == "open" {
			n++
		}
	}
	return
}

func (s *State) snapshotNow() Snapshot {
	w, _ := s.waiting()
	return Snapshot{At: s.Now, Waiting: w, BedsAvailable: s.BedsAvailable, PendingTasks: s.openTasks(), LabTurnaroundMin: s.LabTurnaroundMin}
}

func (s *State) snapshot() { s.History = append(s.History, s.snapshotNow()) }

type Metrics struct {
	ActivePatients   int `json:"activePatients"`
	Waiting          int `json:"waiting"`
	LongestWaitMin   int `json:"longestWaitMin"`
	PendingTasks     int `json:"pendingTasks"`
	BedsAvailable    int `json:"bedsAvailable"`
	BedsTotal        int `json:"bedsTotal"`
	LabTurnaroundMin int `json:"labTurnaroundMin"`
}

type Dashboard struct {
	Simulated bool         `json:"simulated"`
	Now       time.Time    `json:"now"`
	Metrics   Metrics      `json:"metrics"`
	Patients  []*Patient   `json:"patients"`
	Alerts    []*Alert     `json:"alerts"`
	Tasks     []*Task      `json:"tasks"`
	History   []Snapshot   `json:"history"`
	Audit     []AuditEvent `json:"audit"`
}

var severityRank = map[string]int{"high": 0, "medium": 1, "low": 2}

func (s *State) dashboard() Dashboard {
	w, longest := s.waiting()
	alerts := append([]*Alert(nil), s.Alerts...)
	sort.SliceStable(alerts, func(i, j int) bool {
		if severityRank[alerts[i].Severity] != severityRank[alerts[j].Severity] {
			return severityRank[alerts[i].Severity] < severityRank[alerts[j].Severity]
		}
		return alerts[i].CreatedAt.Before(alerts[j].CreatedAt)
	})
	return Dashboard{
		Simulated: true,
		Now:       s.Now,
		Metrics: Metrics{
			ActivePatients: len(s.Patients), Waiting: w, LongestWaitMin: longest, PendingTasks: s.openTasks(),
			BedsAvailable: s.BedsAvailable, BedsTotal: s.BedsTotal, LabTurnaroundMin: s.LabTurnaroundMin,
		},
		Patients: s.Patients,
		Alerts:   alerts,
		Tasks:    s.Tasks,
		History:  s.History,
		Audit:    s.Audit,
	}
}
