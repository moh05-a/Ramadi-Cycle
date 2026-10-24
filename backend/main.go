package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"sync"
)

var (
	mu sync.Mutex
	st = newState()
)

func main() {
	http.HandleFunc("GET /api/dashboard", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		writeJSON(w, http.StatusOK, st.dashboard())
	})

	http.HandleFunc("GET /api/audit", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		writeJSON(w, http.StatusOK, st.Audit)
	})

	http.HandleFunc("POST /api/scenarios/{id}/run", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		if err := st.runScenario(r.PathValue("id")); err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, st.dashboard())
	})

	http.HandleFunc("POST /api/alerts/{id}/review", func(w http.ResponseWriter, r *http.Request) {
		var req ReviewRequest
		if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<16)).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
			return
		}
		mu.Lock()
		defer mu.Unlock()
		if err := st.review(r.PathValue("id"), req); err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, st.dashboard())
	})

	log.Println("CARE API (simulated) listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func writeErr(w http.ResponseWriter, err error) {
	code := http.StatusBadRequest
	if errors.Is(err, errNotFound) {
		code = http.StatusNotFound
	}
	writeJSON(w, code, map[string]string{"error": err.Error()})
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}
