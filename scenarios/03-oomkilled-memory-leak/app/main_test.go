package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func resetLeak() {
	leakMu.Lock()
	leakStore = nil
	leakMu.Unlock()
	leakCalls.Store(0)
}

func TestHealthEndpoints(t *testing.T) {
	for _, path := range []string{"/healthz", "/ready"} {
		req := httptest.NewRequest(http.MethodGet, path, nil)
		rr := httptest.NewRecorder()
		healthHandler(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("%s: expected 200, got %d", path, rr.Code)
		}
		if rr.Body.String() != "ok" {
			t.Errorf("%s: expected body 'ok', got %q", path, rr.Body.String())
		}
	}
}

func TestLeakHandlerAllocatesMemory(t *testing.T) {
	resetLeak()

	req := httptest.NewRequest(http.MethodGet, "/leak", nil)
	rr := httptest.NewRecorder()
	leakHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}

	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON response: %v", err)
	}

	// After one call there should be exactly 1 chunk
	chunkNumber, ok := body["chunk_number"].(float64)
	if !ok || chunkNumber != 1 {
		t.Errorf("expected chunk_number=1, got %v", body["chunk_number"])
	}

	resetLeak()
}

func TestLeakHandlerAccumulates(t *testing.T) {
	resetLeak()

	for i := 0; i < 3; i++ {
		req := httptest.NewRequest(http.MethodGet, "/leak", nil)
		rr := httptest.NewRecorder()
		leakHandler(rr, req)
		if rr.Code != http.StatusOK {
			t.Fatalf("call %d: expected 200, got %d", i+1, rr.Code)
		}
	}

	// leakStore should now hold 3 chunks
	leakMu.Lock()
	count := len(leakStore)
	leakMu.Unlock()

	if count != 3 {
		t.Errorf("expected 3 chunks in leakStore, got %d", count)
	}

	resetLeak()
}

func TestStatsEndpoint(t *testing.T) {
	resetLeak()

	req := httptest.NewRequest(http.MethodGet, "/stats", nil)
	rr := httptest.NewRecorder()
	statsHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	if ct := rr.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("expected Content-Type application/json, got %q", ct)
	}

	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}

	for _, key := range []string{"leak_chunks", "leak_mb", "runtime_alloc_mb", "runtime_sys_mb", "goroutines"} {
		if _, ok := body[key]; !ok {
			t.Errorf("missing expected key %q in stats response", key)
		}
	}
}

func TestLeakStoreGrowsMonotonically(t *testing.T) {
	resetLeak()

	const calls = 5
	for i := 0; i < calls; i++ {
		req := httptest.NewRequest(http.MethodGet, "/leak", nil)
		rr := httptest.NewRecorder()
		leakHandler(rr, req)

		var body map[string]any
		json.Unmarshal(rr.Body.Bytes(), &body)
		expected := float64(i + 1)
		if body["chunk_number"] != expected {
			t.Errorf("call %d: expected chunk_number=%v, got %v", i+1, expected, body["chunk_number"])
		}
	}

	// Memory is never freed — store should still hold all chunks
	leakMu.Lock()
	finalCount := len(leakStore)
	leakMu.Unlock()

	if finalCount != calls {
		t.Errorf("expected %d chunks, got %d", calls, finalCount)
	}

	resetLeak()
}
