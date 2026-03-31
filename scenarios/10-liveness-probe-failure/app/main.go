/*
Scenario 10: Liveness Probe Failure – App Deadlock
===================================================
This Go HTTP server simulates an application that enters a deadlock after
handling a configurable number of work requests.  Once deadlocked, the
/healthz endpoint blocks indefinitely because it too depends on the
stuck mutex.  Kubernetes detects the liveness probe timeout and restarts
the container, producing increasing RESTARTS counts.

How the deadlock works:
  1. The server handles the first DEADLOCK_AFTER requests to /work normally.
  2. On request (DEADLOCK_AFTER + 1), a background goroutine acquires the
     global workMu mutex and holds it permanently.
  3. All subsequent /healthz calls try to acquire workMu — they block
     forever because workMu is never released.
  4. Kubernetes times out the liveness probe (timeoutSeconds: 3) and after
     failureThreshold: 2 consecutive failures, kills and restarts the pod.

Endpoints:
  GET /work    — simulate a unit of work (triggers deadlock after N calls)
  GET /healthz — liveness probe (hangs after deadlock is triggered)
  GET /ready   — readiness probe (same as /healthz)
  GET /status  — JSON report of request count and deadlock state

Environment variables:
  APP_PORT       — port to listen on (default: 8080)
  DEADLOCK_AFTER — number of /work requests before deadlock (default: 5)
*/
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

// workMu is the shared mutex.  A background goroutine acquires it permanently
// after DEADLOCK_AFTER work requests, causing /healthz to block.
var (
	workMu       sync.Mutex
	requestCount atomic.Int64
	deadlocked   atomic.Bool
)

func deadlockAfterN() int {
	v := os.Getenv("DEADLOCK_AFTER")
	if v == "" {
		return 5
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return 5
	}
	return n
}

// workHandler processes a unit of work.  After deadlockAfter calls it
// spawns a goroutine that acquires workMu and holds it forever.
func workHandler(deadlockAfter int) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		count := requestCount.Add(1)

		// Trigger deadlock on the (deadlockAfter + 1)-th call
		if count > int64(deadlockAfter) && deadlocked.CompareAndSwap(false, true) {
			log.Printf("DEADLOCK: triggering mutex hold after %d requests — /healthz will now block", count)
			// This goroutine acquires the mutex and never releases it.
			go func() {
				workMu.Lock()
				log.Printf("DEADLOCK: workMu held permanently; liveness probe will time out")
				// Hold forever — the OOM killer or Kubernetes will restart us.
				time.Sleep(365 * 24 * time.Hour)
			}()
			// Brief sleep so the goroutine above can acquire the lock first.
			time.Sleep(20 * time.Millisecond)
		}

		if !deadlocked.Load() {
			// Normal work path: acquire and quickly release the mutex.
			workMu.Lock()
			time.Sleep(5 * time.Millisecond)
			workMu.Unlock()
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"request_number": count,
			"deadlocked":     deadlocked.Load(),
			"deadlock_after": deadlockAfter,
		})
	}
}

// healthHandler acquires workMu before responding with "ok".
// After the deadlock is triggered, this call blocks indefinitely —
// Kubernetes times out the probe and marks the pod unhealthy.
func healthHandler(w http.ResponseWriter, r *http.Request) {
	workMu.Lock()
	defer workMu.Unlock()
	fmt.Fprint(w, "ok")
}

// statusHandler always responds immediately (does not use workMu).
func statusHandler(deadlockAfter int) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"request_count":  requestCount.Load(),
			"deadlocked":     deadlocked.Load(),
			"deadlock_after": deadlockAfter,
		})
	}
}

func main() {
	n := deadlockAfterN()

	port := os.Getenv("APP_PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/work", workHandler(n))
	mux.HandleFunc("/healthz", healthHandler)
	mux.HandleFunc("/ready", healthHandler)
	mux.HandleFunc("/status", statusHandler(n))

	log.Printf("Scenario 10 server starting on port %s", port)
	log.Printf("  GET /work    — process a work unit (triggers deadlock after %d calls)", n)
	log.Printf("  GET /healthz — liveness probe (hangs after deadlock)")
	log.Printf("  GET /status  — deadlock state (always responds)")

	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
