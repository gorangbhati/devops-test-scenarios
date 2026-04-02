# Scenario 16: Background Goroutine Panic – Empty Slice Out-of-Bounds

## Overview

This scenario demonstrates a **subtle Go runtime panic triggered by a background goroutine** operating on an empty data structure after a legitimate "season reset" operation.

A game-score REST API runs a background goroutine every `STATS_INTERVAL_SEC` seconds to pre-compute aggregate statistics (min, max, average). The HTTP handler for `/api/scores/stats` correctly handles the empty-store case. However, the background goroutine calls `computeStats` unconditionally — it lacks the same empty-slice guard.

When an operator resets the leaderboard for a new season (`DELETE /api/scores`), the next background tick panics:

```
panic: runtime error: index out of range [0] with length 0

goroutine N [running]:
main.computeStats(...)
        /app/main.go:NN +0xNN
main.statsLoop(...)
        /app/main.go:NN +0xNN
```

Because the panic happens in a goroutine started from `main()` — not inside an HTTP handler — `net/http`'s built-in panic recovery does **not** apply. The entire process exits, and Kubernetes enters `CrashLoopBackOff`.

## Why QA Missed It

| Test scenario | Outcome |
|---|---|
| Submit scores, call `/api/scores/stats` | ✅ Works — data is present |
| Call `/api/scores/stats` with empty store | ✅ Works — HTTP handler has guard |
| Reset scores, then call `/api/scores/stats` | ✅ Works — HTTP handler has guard |
| Reset scores, **wait for background tick** | ❌ Never tested — runs > `STATS_INTERVAL_SEC` |

Test runs complete in well under 30 seconds, so the background goroutine never fires during testing.

## Directory Structure

```
16-background-goroutine-panic/
├── app/
│   ├── main.go         # Go server with the background panic bug
│   ├── main_test.go    # Tests that pass — missing the edge-case coverage
│   ├── go.mod
│   └── Dockerfile
└── k8s/
    ├── configmap.yaml  # SEED_SCORES: "10", STATS_INTERVAL_SEC: "30"
    ├── deployment.yaml
    └── service.yaml
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/scores` | List all submitted scores |
| `POST` | `/api/scores` | Submit a new score `{"player_id":"x","score":1234}` |
| `DELETE` | `/api/scores` | Clear all scores (season reset) |
| `GET` | `/api/scores/stats` | Cached aggregate statistics |
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/ready` | Readiness probe |

## Reproducing the Scenario

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/scenario-16-bg-panic

kubectl port-forward svc/scenario-16-bg-panic 8080:80

# 1. Verify the service is healthy
curl http://localhost:8080/healthz
curl http://localhost:8080/api/scores/stats
# {"count":10,"min":...,"max":...,"average":...}

# 2. Trigger the season reset
curl -X DELETE http://localhost:8080/api/scores
# {"message":"score store cleared","removed":10}

# 3. The stats endpoint immediately returns the safe empty response
curl http://localhost:8080/api/scores/stats
# {"count":0,"message":"no scores yet"}

# 4. Wait for the background goroutine to fire (~30 s)
#    The pod will crash. Watch it:
kubectl get pods -l scenario=16-background-goroutine-panic -w
# NAME                         READY   STATUS             RESTARTS
# scenario-16-bg-panic-xxxxx   1/1     Running            0
# scenario-16-bg-panic-xxxxx   0/1     Error              1
# scenario-16-bg-panic-xxxxx   0/1     CrashLoopBackOff   1
```

## Confirming the Panic

```bash
kubectl logs -l scenario=16-background-goroutine-panic --previous
# goroutine 6 [running]:
# main.computeStats(...)
#         /app/main.go:NN
# main.statsLoop(...)
#         /app/main.go:NN
# ...
# exit status 2
```

## Root Cause in Code

In `main.go`, the HTTP handler guards against the empty store:

```go
func statsHandler(w http.ResponseWriter, r *http.Request) {
    mu.RLock()
    count := len(scoreStore)
    mu.RUnlock()

    if count == 0 {                          // ← guard present in HTTP path
        json.NewEncoder(w).Encode(...)
        return
    }
    ...
}
```

But the background goroutine does not:

```go
func statsLoop(interval time.Duration) {
    for range ticker.C {
        mu.RLock()
        scores := make([]int, len(scoreStore))
        ...
        mu.RUnlock()

        computed := computeStats(scores)  // ← no guard; panics when len==0
    }
}
```

And `computeStats` itself:

```go
func computeStats(scores []int) Stats {
    n := len(scores)
    sort.Ints(scores)
    ...
    return Stats{
        Min: scores[0],   // panic when n == 0
        Max: scores[n-1], // panic when n == 0
        ...
    }
}
```

## Fix

Add an early-return guard in `statsLoop` (or inside `computeStats`):

```go
// Option A — guard in the goroutine
if len(scores) == 0 {
    log.Println("Stats aggregator: no scores yet, skipping tick")
    continue
}
computed := computeStats(scores)

// Option B — guard inside computeStats
func computeStats(scores []int) Stats {
    if len(scores) == 0 {
        return Stats{}
    }
    ...
}
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:

- `RESTARTS` count increasing for a pod that had been running successfully
- `kubectl logs --previous` shows `panic: runtime error: index out of range [0] with length 0`
- Stack trace consistently points to `main.computeStats` → `main.statsLoop`
- Pod crash timing correlates with `STATS_INTERVAL_SEC` after the reset operation
- The HTTP endpoint `/api/scores/stats` responds correctly (`{"count":0}`) while the background goroutine panics — this mismatch is the key clue
- `kubectl describe pod` events show `Back-off restarting failed container`
