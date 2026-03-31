# Scenario 10: Liveness Probe Failure – App Deadlock

## Overview

This scenario demonstrates a Go application that enters a **mutex deadlock** after handling a configurable number of requests. Once deadlocked, the `/healthz` endpoint blocks indefinitely. Kubernetes detects the liveness probe timeout and repeatedly restarts the container, producing increasing `RESTARTS` counts.

## How the Deadlock Works

```
Request 1–5  → /work processes normally (acquires and releases workMu)
Request 6    → background goroutine acquires workMu and NEVER releases it
Request 7+   → /work skips the mutex (deadlocked flag set)
/healthz     → tries to acquire workMu → BLOCKS FOREVER
Kubernetes   → times out liveness probe (timeoutSeconds: 3)
             → after 2 failures: kills and restarts container
```

## Directory Structure

```
10-liveness-probe-failure/
├── app/
│   ├── main.go         # Go server with deliberate deadlock
│   ├── main_test.go    # Go unit tests
│   ├── go.mod
│   └── Dockerfile
├── k8s/
│   ├── configmap.yaml   # DEADLOCK_AFTER: "5"
│   ├── deployment.yaml  # livenessProbe with short timeout
│   └── service.yaml
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /work` | Process a work unit; triggers deadlock after `DEADLOCK_AFTER` calls |
| `GET /healthz` | Liveness probe — blocks permanently after deadlock |
| `GET /ready` | Same as `/healthz` |
| `GET /status` | Always responds — reports current request count and deadlock state |

## Reproducing the Scenario

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/scenario-10-liveness-probe

kubectl port-forward svc/scenario-10-liveness-probe 8080:80

# Trigger the deadlock (make 6+ requests with default DEADLOCK_AFTER=5)
for i in $(seq 1 7); do
  curl -s http://localhost:8080/work | jq
  sleep 1
done

# /status always responds (does not use workMu)
curl -s http://localhost:8080/status | jq
# { "deadlocked": true, "request_count": 7, "deadlock_after": 5 }

# Watch pod restarts
kubectl get pods -l scenario=10-liveness-probe-failure -w
# RESTARTS column will increment every ~20–30s
```

## Confirming the Liveness Probe Failure

```bash
kubectl describe pod -l scenario=10-liveness-probe-failure
# Events:
#   Warning  Unhealthy  Liveness probe failed: Get ".../healthz": context deadline exceeded
#   Normal   Killing    Container app failed liveness probe, will be restarted
```

## Fixing the Scenario

**Option A — Fix the code:** ensure the health handler does not depend on `workMu`:
```go
func healthHandler(w http.ResponseWriter, r *http.Request) {
    // Don't acquire workMu here
    fmt.Fprint(w, "ok")
}
```

**Option B — Remove the deadlock:** protect the mutex acquisition with a timeout using `TryLock()` (Go 1.18+):
```go
if !workMu.TryLock() {
    w.WriteHeader(http.StatusServiceUnavailable)
    fmt.Fprint(w, "busy")
    return
}
defer workMu.Unlock()
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- `RESTARTS` count increasing for a pod that started successfully
- `kubectl describe pod` events: `Liveness probe failed: context deadline exceeded`
- `/status` endpoint responds immediately while `/healthz` hangs
- Container logs show `DEADLOCK: workMu held permanently` before restarts
- Increasing restart frequency matches liveness probe `periodSeconds × failureThreshold`
