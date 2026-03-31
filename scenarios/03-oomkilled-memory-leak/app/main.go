/*
Scenario 03: Container OOMKilled – Memory Leak
===============================================
This Go HTTP server deliberately leaks memory by appending large byte-slices
to a global slice on every request to /leak.  With a tight memory limit in
the Kubernetes Deployment (e.g. 32Mi), the container will be killed by the
Linux OOM killer after a handful of requests, causing the pod to restart with
reason OOMKilled.

Endpoints:
  GET /leak    — allocates ALLOC_MB megabytes and appends to the global leak store
  GET /healthz — liveness probe (always 200 while the process is alive)
  GET /ready   — readiness probe (always 200 while the process is alive)
  GET /stats   — reports current leak store size and Go runtime memory stats

Environment variables:
  APP_PORT  — port to listen on (default: 8080)
  ALLOC_MB  — megabytes to allocate per /leak call (default: 10)
*/
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"sync"
	"sync/atomic"
)

// leakStore holds all allocated slices — they are never freed.
// This is the intentional memory leak.
var (
	leakStore [][]byte
	leakMu    sync.Mutex
	leakCalls atomic.Int64
)

func allocMB() int {
	v := os.Getenv("ALLOC_MB")
	if v == "" {
		return 10
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return 10
	}
	return n
}

// leakHandler allocates ALLOC_MB of memory and keeps a reference to it.
func leakHandler(w http.ResponseWriter, r *http.Request) {
	mb := allocMB()
	chunk := make([]byte, mb*1024*1024)
	// Touch every page to ensure the OS actually maps the memory.
	for i := range chunk {
		chunk[i] = byte(i)
	}

	leakMu.Lock()
	leakStore = append(leakStore, chunk)
	count := int64(len(leakStore))
	leakMu.Unlock()

	leakCalls.Add(1)

	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)

	log.Printf("LEAK: allocated %dMB chunk #%d  total_alloc=%dMB  sys=%dMB",
		mb, count,
		ms.TotalAlloc/1024/1024,
		ms.Sys/1024/1024,
	)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"chunk_number": count,
		"chunk_mb":     mb,
		"total_chunks": count,
		"total_mb":     count * int64(mb),
	})
}

// statsHandler reports in-process memory metrics.
func statsHandler(w http.ResponseWriter, r *http.Request) {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)

	leakMu.Lock()
	chunks := len(leakStore)
	leakMu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"leak_chunks":       chunks,
		"leak_mb":           chunks * allocMB(),
		"runtime_alloc_mb":  ms.Alloc / 1024 / 1024,
		"runtime_sys_mb":    ms.Sys / 1024 / 1024,
		"goroutines":        runtime.NumGoroutine(),
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "ok")
}

func main() {
	port := os.Getenv("APP_PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/leak", leakHandler)
	mux.HandleFunc("/stats", statsHandler)
	mux.HandleFunc("/healthz", healthHandler)
	mux.HandleFunc("/ready", healthHandler)

	log.Printf("Scenario 03 server starting on port %s", port)
	log.Printf("  GET /leak    — allocate %dMB and keep reference (leaks memory)", allocMB())
	log.Printf("  GET /stats   — show memory usage")
	log.Printf("  GET /healthz — liveness probe")
	log.Printf("  GET /ready   — readiness probe")

	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
