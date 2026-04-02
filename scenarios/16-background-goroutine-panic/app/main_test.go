package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// resetState clears all global state so that tests run independently.
func resetState() {
	mu.Lock()
	scoreStore = scoreStore[:0]
	nextID = 0
	mu.Unlock()

	statsMu.Lock()
	cachedStats = nil
	statsMu.Unlock()
}

func TestHealthEndpoint(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rr := httptest.NewRecorder()
	healthHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	if rr.Body.String() != "ok" {
		t.Errorf("expected body 'ok', got %q", rr.Body.String())
	}
}

func TestSubmitScore_Valid(t *testing.T) {
	resetState()

	body := strings.NewReader(`{"player_id":"alice","score":1500}`)
	req := httptest.NewRequest(http.MethodPost, "/api/scores", body)
	rr := httptest.NewRecorder()
	submitScoreHandler(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rr.Code, rr.Body.String())
	}

	var entry ScoreEntry
	if err := json.Unmarshal(rr.Body.Bytes(), &entry); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if entry.PlayerID != "alice" {
		t.Errorf("expected player_id=alice, got %q", entry.PlayerID)
	}
	if entry.Score != 1500 {
		t.Errorf("expected score=1500, got %d", entry.Score)
	}
}

func TestSubmitScore_MissingPlayerID(t *testing.T) {
	resetState()

	body := strings.NewReader(`{"score":100}`)
	req := httptest.NewRequest(http.MethodPost, "/api/scores", body)
	rr := httptest.NewRecorder()
	submitScoreHandler(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rr.Code)
	}
}

func TestListScores(t *testing.T) {
	resetState()
	seedScores(5)

	req := httptest.NewRequest(http.MethodGet, "/api/scores", nil)
	rr := httptest.NewRecorder()
	listScoresHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}

	var entries []ScoreEntry
	if err := json.Unmarshal(rr.Body.Bytes(), &entries); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if len(entries) != 5 {
		t.Errorf("expected 5 entries, got %d", len(entries))
	}
}

func TestResetScores(t *testing.T) {
	resetState()
	seedScores(5)

	req := httptest.NewRequest(http.MethodDelete, "/api/scores", nil)
	rr := httptest.NewRecorder()
	resetScoresHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}

	mu.RLock()
	remaining := len(scoreStore)
	mu.RUnlock()

	if remaining != 0 {
		t.Errorf("expected empty store after reset, got %d entries", remaining)
	}
}

// TestStatsEndpoint_EmptyStore verifies that the HTTP handler returns a safe
// {"count": 0} response when the score store is empty.
//
// NOTE: this test passes because the HTTP handler has an explicit empty-store
// guard.  The background goroutine (statsLoop) does NOT have this guard —
// it calls computeStats unconditionally, panicking on an empty slice.
// That code path is never exercised by the test suite.
func TestStatsEndpoint_EmptyStore(t *testing.T) {
	resetState()

	req := httptest.NewRequest(http.MethodGet, "/api/scores/stats", nil)
	rr := httptest.NewRecorder()
	statsHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}

	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if count, _ := body["count"].(float64); int(count) != 0 {
		t.Errorf("expected count=0, got %v", body["count"])
	}
}

func TestStatsEndpoint_WithCachedData(t *testing.T) {
	resetState()
	seedScores(3)

	// Pre-populate the cache to simulate what statsLoop would produce.
	statsMu.Lock()
	cachedStats = &Stats{Count: 3, Min: 1000, Max: 3000, Average: 2000.0}
	statsMu.Unlock()

	req := httptest.NewRequest(http.MethodGet, "/api/scores/stats", nil)
	rr := httptest.NewRecorder()
	statsHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
}

// TestComputeStats_NormalCase verifies computeStats for a typical non-empty input.
//
// This is the only test for computeStats.  The empty-input edge case is never
// tested, which hides the panic bug until it fires in production after a
// season reset empties the score store.
func TestComputeStats_NormalCase(t *testing.T) {
	scores := []int{500, 100, 300, 200, 400}
	stats := computeStats(scores)

	if stats.Count != 5 {
		t.Errorf("expected Count=5, got %d", stats.Count)
	}
	if stats.Min != 100 {
		t.Errorf("expected Min=100, got %d", stats.Min)
	}
	if stats.Max != 500 {
		t.Errorf("expected Max=500, got %d", stats.Max)
	}
	if stats.Average != 300.0 {
		t.Errorf("expected Average=300.0, got %f", stats.Average)
	}
}
