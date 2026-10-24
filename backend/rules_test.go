package main

import "testing"

func statuses(s *State) map[string]string {
	m := map[string]string{}
	for _, a := range s.Alerts {
		m[a.Rule+"|"+a.CaseID+"|"+a.TaskID] = a.Status
	}
	return m
}

func has(s *State, rule string) *Alert {
	for _, a := range s.Alerts {
		if a.Rule == rule && a.Status == "open" {
			return a
		}
	}
	return nil
}

func TestBaseline(t *testing.T) {
	s := newState()
	if has(s, "overdue_reassessment") == nil || has(s, "missing_field") == nil {
		t.Fatalf("baseline should flag overdue reassessment and missing field, got %v", statuses(s))
	}
	if len(s.Alerts) != 2 {
		t.Fatalf("want 2 baseline alerts, got %v", statuses(s))
	}
}

func TestScenarios(t *testing.T) {
	cases := []struct {
		steps []string
		want  string
	}{
		{[]string{"stable"}, "overdue_task"},
		{[]string{"stable", "surge"}, "queue_pressure"},
		{[]string{"surge"}, "lab_delay"},
		{[]string{"lab_delay"}, "lab_delay"},
		{[]string{"bed_block"}, "bed_bottleneck"},
	}
	for _, c := range cases {
		s := newState()
		for _, step := range c.steps {
			if err := s.runScenario(step); err != nil {
				t.Fatal(err)
			}
		}
		if has(s, c.want) == nil {
			t.Errorf("%v: want open %s, got %v", c.steps, c.want, statuses(s))
		}
	}
	if err := newState().runScenario("nope"); err != errNotFound {
		t.Errorf("unknown scenario should be errNotFound, got %v", err)
	}
}

func TestResetIsReproducible(t *testing.T) {
	s := newState()
	want := statuses(s)
	s.runScenario("surge")
	s.runScenario("reset")
	got := statuses(s)
	if len(got) != len(want) || len(s.History) != 1 || len(s.Audit) != 0 {
		t.Fatalf("reset not clean: %v vs %v", got, want)
	}
}

func TestReview(t *testing.T) {
	s := newState()
	s.runScenario("bed_block")
	a := has(s, "bed_bottleneck")

	if err := s.review(a.ID, ReviewRequest{Decision: "override", ReviewerRole: "charge_nurse"}); err == nil {
		t.Fatal("override without reason must fail")
	}
	if err := s.review(a.ID, ReviewRequest{Decision: "override", Reason: "transfer arriving", ReviewerRole: "charge_nurse"}); err != nil {
		t.Fatal(err)
	}
	if a.Status != "overridden" || len(s.Audit) != 1 || s.Audit[0].Reason != "transfer arriving" {
		t.Fatalf("override not recorded: %+v %+v", a, s.Audit)
	}
	// stays closed on re-evaluation while condition persists
	s.evaluate()
	if a.Status != "overridden" {
		t.Fatalf("closed alert reopened: %s", a.Status)
	}
	if err := s.review(a.ID, ReviewRequest{Decision: "acknowledge", ReviewerRole: "x"}); err == nil {
		t.Fatal("reviewing a closed alert must fail")
	}

	// completing a reassessment updates the patient and resolves the alert
	r := has(s, "overdue_reassessment")
	if err := s.review(r.ID, ReviewRequest{Decision: "complete", ReviewerRole: "clinician"}); err != nil {
		t.Fatal(err)
	}
	if has(s, "overdue_reassessment") != nil {
		t.Fatal("reassessment alert still open after complete")
	}
}
