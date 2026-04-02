/*
Scenario 16: Game Score Service – Background Goroutine Panic on Empty Scores
=============================================================================
A REST API for submitting and tracking game scores.  A background goroutine
periodically computes aggregate statistics (min, max, average) and caches the
result so the /api/scores/stats endpoint can respond instantly.

The application contains a subtle bug in computeStats:

	func computeStats(scores []int) Stats {
	    ...
	    return Stats{Min: scores[0], Max: scores[n-1], ...}  // panics when empty
	}

The HTTP handler for /api/scores/stats correctly guards against an empty
score list and returns {"count": 0} in that case.  However, the background
goroutine that calls computeStats does NOT include the same guard.

After all scores are cleared (e.g. via DELETE /api/scores to start a new
season), the next background aggregation tick panics with:

	panic: runtime error: index out of range [0] with length 0

Because the panic occurs inside a goroutine launched by main() — not inside
an HTTP handler — it is NOT recovered by net/http.  The entire process exits
and Kubernetes enters CrashLoopBackOff.

Why QA missed it:
  - Unit tests call computeStats only with non-empty slices.
  - Integration tests call /api/scores/stats with an empty store and observe
    the correct {"count": 0} response — the HTTP guard works fine.
  - No test covers the background goroutine path with an empty score list,
    because test runs complete in well under STATS_INTERVAL_SEC seconds.

Environment variables (via ConfigMap):
  APP_PORT           — HTTP listen port (default: 8080)
  SEED_SCORES        — Scores to seed on startup (default: 10)
  STATS_INTERVAL_SEC — Background aggregation interval in seconds (default: 30)
*/
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"sort"
	"strconv"
	"sync"
	"time"
)

// ScoreEntry holds a single submitted score.
type ScoreEntry struct {
	ID        int       `json:"id"`
	PlayerID  string    `json:"player_id"`
	Score     int       `json:"score"`
	CreatedAt time.Time `json:"created_at"`
}

// Stats is the pre-computed aggregate cached by the background goroutine.
type Stats struct {
	Count   int     `json:"count"`
	Min     int     `json:"min"`
	Max     int     `json:"max"`
	Average float64 `json:"average"`
}

var (
	mu          sync.RWMutex
	scoreStore  []ScoreEntry
	nextID      int

	statsMu     sync.RWMutex
	cachedStats *Stats
)

// envInt reads an integer environment variable, returning defaultVal on any error.
func envInt(key string, defaultVal int) int {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < 0 {
		return defaultVal
	}
	return n
}

// seedScores pre-populates the score store with n random entries.
func seedScores(n int) {
	if n == 0 {
		log.Println("No seed scores configured — store starts empty")
		return
	}
	mu.Lock()
	defer mu.Unlock()
	for i := 0; i < n; i++ {
		nextID++
		scoreStore = append(scoreStore, ScoreEntry{
			ID:        nextID,
			PlayerID:  fmt.Sprintf("player-%03d", i+1),
			Score:     rand.Intn(9001) + 1000, // 1000–10000
			CreatedAt: time.Now().Add(-time.Duration(i) * time.Minute),
		})
	}
	log.Printf("Seeded %d scores", n)
}

// computeStats calculates aggregate statistics for a slice of raw scores.
//
// BUG: this function does not guard against an empty input slice.
// Accessing scores[0] and scores[n-1] when n == 0 causes:
//
//	panic: runtime error: index out of range [0] with length 0
//
// The /api/scores/stats HTTP handler correctly returns early when the store
// is empty, but the background statsLoop goroutine calls computeStats
// unconditionally — it never reaches the HTTP layer's guard.
func computeStats(scores []int) Stats {
	n := len(scores)
	sort.Ints(scores)

	total := 0
	for _, s := range scores {
		total += s
	}

	return Stats{
		Count:   n,
		Min:     scores[0],   // panic: index out of range when n == 0
		Max:     scores[n-1], // panic: index out of range when n == 0
		Average: float64(total) / float64(n),
	}
}

// statsLoop is the background goroutine that recomputes aggregate statistics
// on each tick and stores the result in cachedStats.
//
// Panics in this goroutine are NOT recovered — they crash the whole process.
func statsLoop(interval time.Duration) {
	log.Printf("Stats aggregator starting (interval: %s)", interval)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		mu.RLock()
		scores := make([]int, len(scoreStore))
		for i, s := range scoreStore {
			scores[i] = s.Score
		}
		mu.RUnlock()

		// BUG: computeStats is called without guarding for an empty slice.
		// When the score store is empty (e.g. after DELETE /api/scores),
		// this goroutine panics and kills the entire process.
		computed := computeStats(scores)

		statsMu.Lock()
		cachedStats = &computed
		statsMu.Unlock()

		log.Printf("Stats updated: count=%d min=%d max=%d avg=%.2f",
			computed.Count, computed.Min, computed.Max, computed.Average)
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// HTTP Handlers
// ─────────────────────────────────────────────────────────────────────────────

func listScoresHandler(w http.ResponseWriter, r *http.Request) {
	mu.RLock()
	snapshot := make([]ScoreEntry, len(scoreStore))
	copy(snapshot, scoreStore)
	mu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(snapshot)
}

func submitScoreHandler(w http.ResponseWriter, r *http.Request) {
	var body struct {
		PlayerID string `json:"player_id"`
		Score    int    `json:"score"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}
	if body.PlayerID == "" {
		http.Error(w, "player_id is required", http.StatusBadRequest)
		return
	}
	if body.Score < 0 {
		http.Error(w, "score must be non-negative", http.StatusBadRequest)
		return
	}

	mu.Lock()
	nextID++
	entry := ScoreEntry{
		ID:        nextID,
		PlayerID:  body.PlayerID,
		Score:     body.Score,
		CreatedAt: time.Now(),
	}
	scoreStore = append(scoreStore, entry)
	mu.Unlock()

	log.Printf("Score submitted: player=%s score=%d id=%d", entry.PlayerID, entry.Score, entry.ID)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(entry)
}

// statsHandler serves cached aggregate statistics.
// It correctly handles the empty-store case and returns {"count": 0}.
// Note: the background goroutine (statsLoop) does NOT have this same guard.
func statsHandler(w http.ResponseWriter, r *http.Request) {
	mu.RLock()
	count := len(scoreStore)
	mu.RUnlock()

	if count == 0 {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"count": 0, "message": "no scores yet"})
		return
	}

	statsMu.RLock()
	stats := cachedStats
	statsMu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	if stats == nil {
		json.NewEncoder(w).Encode(map[string]any{"count": count, "message": "stats computing…"})
		return
	}
	json.NewEncoder(w).Encode(stats)
}

func resetScoresHandler(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	prev := len(scoreStore)
	scoreStore = scoreStore[:0]
	nextID = 0
	mu.Unlock()

	statsMu.Lock()
	cachedStats = nil
	statsMu.Unlock()

	log.Printf("Score store cleared: %d entries removed (season reset)", prev)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"message": "score store cleared",
		"removed": prev,
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "ok")
}

func scoresRouter(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		listScoresHandler(w, r)
	case http.MethodPost:
		submitScoreHandler(w, r)
	case http.MethodDelete:
		resetScoresHandler(w, r)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

// ─────────────────────────────────────────────────────────────────────────────

func main() {
	port := os.Getenv("APP_PORT")
	if port == "" {
		port = "8080"
	}

	seedCount := envInt("SEED_SCORES", 10)
	statsIntervalSec := envInt("STATS_INTERVAL_SEC", 30)

	seedScores(seedCount)

	go statsLoop(time.Duration(statsIntervalSec) * time.Second)

	mux := http.NewServeMux()
	mux.HandleFunc("/api/scores", scoresRouter)
	mux.HandleFunc("/api/scores/stats", statsHandler)
	mux.HandleFunc("/healthz", healthHandler)
	mux.HandleFunc("/ready", healthHandler)

	log.Printf("Scenario 16 server starting on port %s", port)
	log.Printf("  GET    /api/scores       — list all scores")
	log.Printf("  POST   /api/scores       — submit a new score")
	log.Printf("  DELETE /api/scores       — clear all scores (season reset)")
	log.Printf("  GET    /api/scores/stats — aggregate statistics (cached)")
	log.Printf("  STATS_INTERVAL_SEC=%d   — background aggregation interval", statsIntervalSec)

	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
