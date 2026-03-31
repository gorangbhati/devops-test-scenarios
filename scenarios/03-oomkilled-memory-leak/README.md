# Scenario 03: Container OOMKilled – Memory Leak

## Overview

This scenario demonstrates a container being killed by the Linux OOM (Out-Of-Memory)
killer — one of the most common production incidents in Kubernetes.

The Go HTTP server intentionally **leaks memory**: every request to `/leak` allocates a
chunk of memory and appends it to a global slice that is never freed. With a deliberately
tight memory limit (`32Mi`) in the Deployment, just a few requests cause the container
to exceed its limit and be terminated by the kernel.

## What Happens

| Step | Action |
|------|--------|
| 1 | Deployment starts with `memory: 32Mi` limit |
| 2 | A client (or agent) hits `GET /leak` repeatedly |
| 3 | Each call allocates 10MB and retains a reference |
| 4 | After ~3 calls the container crosses 32Mi |
| 5 | The Linux OOM killer terminates the process |
| 6 | Kubernetes restarts the container; `OOMKilled` appears in pod status |

## Directory Structure

```
03-oomkilled-memory-leak/
├── app/
│   ├── main.go          # Go HTTP server with leak logic
│   ├── main_test.go     # Go unit tests
│   ├── go.mod
│   └── Dockerfile
└── k8s/
    ├── configmap.yaml
    ├── deployment.yaml  # memory limit: 32Mi  ← intentionally tight
    └── service.yaml
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /leak` | Allocates `ALLOC_MB` (default 10) MB and **never frees it** |
| `GET /stats` | Reports current chunk count and Go runtime memory stats |
| `GET /healthz` | Liveness probe — 200 while alive |
| `GET /ready` | Readiness probe — 200 while alive |

## Reproducing the Scenario

```bash
# Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Port-forward
kubectl port-forward svc/scenario-03-oomkilled 8080:80

# Trigger the leak (repeat until OOMKilled)
for i in $(seq 1 5); do
  curl -s http://localhost:8080/leak | jq
  sleep 1
done

# Watch for OOMKilled
kubectl get pods -l scenario=03-oomkilled-memory-leak -w
```

Expected output:
```
NAME                                   READY   STATUS      RESTARTS   AGE
scenario-03-oomkilled-xxxxx-yyyyy      0/1     OOMKilled   1          30s
```

```bash
# Confirm with describe
kubectl describe pod -l scenario=03-oomkilled-memory-leak
# Look for:
#   Last State: Terminated
#     Reason:   OOMKilled
#     Exit Code: 137
```

## Fixing the Scenario

Two options:

1. **Fix the code**: Use a bounded cache with an eviction policy (LRU, TTL, etc.):
   ```go
   // Instead of: leakStore = append(leakStore, chunk)
   // Use an eviction strategy:
   if len(leakStore) >= MAX_CHUNKS {
       leakStore = leakStore[1:] // evict oldest
   }
   leakStore = append(leakStore, chunk)
   ```

2. **Increase the memory limit** (band-aid — doesn't fix the leak):
   ```yaml
   resources:
     limits:
       memory: "512Mi"
   ```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- Pod `reason: OOMKilled` in container state
- Exit code `137` (SIGKILL sent by kernel)
- `kubectl describe pod` shows `Last State: Terminated, Reason: OOMKilled`
- Rising `container_memory_working_set_bytes` metric approaching the limit
- Repeated pod restarts with increasing frequency
- `/stats` endpoint showing `leak_chunks` growing without bound
