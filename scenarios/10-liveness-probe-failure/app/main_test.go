package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// resetState resets all global counters so tests run independently.
func resetState() {
	requestCount.Store(0)
	deadlocked.Store(false)
	workMu = sync.Mutex{}
}

func TestHealthzBeforeDeadlock(t *testing.T) {
	resetState()

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

func TestWorkHandlerIncrementsCounter(t *testing.T) {
	resetState()
	handler := workHandler(10) // high threshold — won't trigger deadlock

	for i := 1; i <= 3; i++ {
		req := httptest.NewRequest(http.MethodGet, "/work", nil)
		rr := httptest.NewRecorder()
		handler(rr, req)

		if rr.Code != http.StatusOK {
			t.Fatalf("call %d: expected 200, got %d", i, rr.Code)
		}

		var body map[string]any
		if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
			t.Fatalf("invalid JSON: %v", err)
		}
		if got := body["request_number"].(float64); int(got) != i {
			t.Errorf("call %d: expected request_number=%d, got %v", i, i, got)
		}
		if body["deadlocked"].(bool) {
			t.Errorf("call %d: deadlocked should be false before threshold", i)
		}
	}
}

func TestDeadlockTriggeredAfterThreshold(t *testing.T) {
	resetState()
	const threshold = 3
	handler := workHandler(threshold)

	// Make threshold+1 requests to trigger the deadlock
	for i := 0; i <= threshold; i++ {
		req := httptest.NewRequest(http.MethodGet, "/work", nil)
		rr := httptest.NewRecorder()
		handler(rr, req)
	}

	// Allow background goroutine to acquire the mutex
	time.Sleep(50 * time.Millisecond)

	if !deadlocked.Load() {
		t.Error("expected deadlocked to be true after threshold+1 requests")
	}
}

func TestStatusHandlerAlwaysResponds(t *testing.T) {
	resetState()
	handler := statusHandler(5)

	req := httptest.NewRequest(http.MethodGet, "/status", nil)
	rr := httptest.NewRecorder()
	handler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}

	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	for _, key := range []string{"request_count", "deadlocked", "deadlock_after"} {
		if _, ok := body[key]; !ok {
			t.Errorf("missing key %q in status response", key)
		}
	}
}

func TestStatusAfterDeadlock(t *testing.T) {
	resetState()
	const threshold = 2
	workH := workHandler(threshold)
	statusH := statusHandler(threshold)

	// Trigger deadlock
	for i := 0; i <= threshold; i++ {
		req := httptest.NewRequest(http.MethodGet, "/work", nil)
		workH(httptest.NewRecorder(), req)
	}
	time.Sleep(50 * time.Millisecond)

	// Status endpoint must still respond immediately (does not use workMu)
	req := httptest.NewRequest(http.MethodGet, "/status", nil)
	rr := httptest.NewRecorder()

	done := make(chan struct{})
	go func() {
		statusH(rr, req)
		close(done)
	}()

	select {
	case <-done:
		// OK — responded quickly
	case <-time.After(2 * time.Second):
		t.Fatal("status endpoint timed out — it must not depend on workMu")
	}

	var body map[string]any
	json.Unmarshal(rr.Body.Bytes(), &body)
	if !body["deadlocked"].(bool) {
		t.Error("status should report deadlocked=true")
	}
}
