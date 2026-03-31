# Scenario 08: Pods Stuck in Pending – Scheduler Failures

## Overview

This scenario demonstrates pods that remain in `Pending` state because **no cluster node satisfies the scheduling constraints** in the Deployment manifest.

Two intentional bugs are present simultaneously:
1. `nodeSelector: hardware: gpu-v100-ultra` — label that exists on no node
2. `resources.requests: cpu: "128", memory: "2Ti"` — exceeds every real cluster node

## What Happens

```
kubectl get pods -l scenario=08-pods-pending-scheduler
NAME                                    READY   STATUS    RESTARTS   AGE
scenario-08-pending-scheduler-xxx-yyy   0/1     Pending   0          5m
```

```
kubectl describe pod -l scenario=08-pods-pending-scheduler
...
Events:
  Type     Reason            Message
  Warning  FailedScheduling  0/3 nodes are available:
                             1 Insufficient cpu,
                             1 Insufficient memory,
                             3 node(s) didn't match Pod's node affinity/selector.
```

## Directory Structure

```
08-pods-pending-scheduler/
├── app/
│   ├── main.py        # Trivial Python healthz server (app is healthy)
│   └── Dockerfile
├── k8s/
│   ├── deployment.yaml  # Impossible nodeSelector + extreme resource requests ← bugs
│   └── service.yaml
└── tests/
    └── test_scheduler_app.py
```

## Reproducing the Scenario

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Pod stays in Pending
kubectl get pods -l scenario=08-pods-pending-scheduler -w

# Inspect scheduler events
kubectl describe pod -l scenario=08-pods-pending-scheduler | grep -A 10 "Events:"
```

## Fixing the Scenario

Edit `k8s/deployment.yaml` and remove the impossible constraints:

```yaml
# Remove nodeSelector entirely, or use a valid label:
# nodeSelector:
#   hardware: gpu-v100-ultra   ← remove this

# Reduce resource requests to realistic values:
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"
```

Then re-apply:
```bash
kubectl apply -f k8s/deployment.yaml
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- Pod in `Pending` state for more than 60 seconds
- `FailedScheduling` events in pod description
- Events mention `Insufficient cpu`, `Insufficient memory`, or `node selector` mismatch
- `kubectl get nodes --show-labels` — no node has `hardware=gpu-v100-ultra`
- `kubectl describe nodes` — CPU and memory capacity far below the requested amounts
