# Scenario 01: CrashLoop due to Bad Config

## Overview

This scenario demonstrates a common Kubernetes anti-pattern: an application that fails
to start because its required configuration is missing or invalid, leading to
**CrashLoopBackOff**.

## What Happens

The Python application (`app/main.py`) validates three required environment variables at
startup:

| Variable | Required Format | Bad Value (default) |
|----------|-----------------|---------------------|
| `DATABASE_URL` | Must start with `postgresql://` | `postgres://…` (wrong scheme) |
| `APP_PORT` | Integer 1–65535 | `not-a-number` |
| `LOG_LEVEL` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR` | `VERBOSE` |

Because the ConfigMap (`k8s/configmap.yaml`) ships with intentionally wrong values, the
application prints an error and exits with code 1 on every start attempt.  Kubernetes
detects the non-zero exit code, backs off, and retries — producing the classic
`CrashLoopBackOff` pattern.

## Directory Structure

```
01-crashloop-bad-config/
├── app/
│   ├── main.py           # Python application
│   ├── requirements.txt  # No external deps (stdlib only)
│   └── Dockerfile
└── k8s/
    ├── configmap.yaml    # ConfigMap with BAD values (triggers the crash)
    └── deployment.yaml   # Deployment referencing the ConfigMap
```

## Reproducing the Scenario

```bash
# Apply the bad ConfigMap and Deployment
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml

# Watch the pod enter CrashLoopBackOff
kubectl get pods -l scenario=01-crashloop-bad-config -w

# See the error message
kubectl logs -l scenario=01-crashloop-bad-config --previous
```

Expected log output:
```
Starting application — validating configuration …
FATAL: Configuration validation failed:
  - DATABASE_URL must start with 'postgresql://', got: 'postgres://user:password@db-host:5432/mydb'
  - APP_PORT must be an integer between 1 and 65535, got: 'not-a-number'
  - LOG_LEVEL must be one of ['DEBUG', 'ERROR', 'INFO', 'WARNING'], got: 'VERBOSE'
```

## Fixing the Scenario

Edit `k8s/configmap.yaml` and set valid values:

```yaml
data:
  DATABASE_URL: "postgresql://user:password@db-host:5432/mydb"
  APP_PORT: "8080"
  LOG_LEVEL: "INFO"
```

Then re-apply:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/scenario-01-crashloop
kubectl rollout status deployment/scenario-01-crashloop
```

## Troubleshooting Checklist

1. `kubectl get pods -l scenario=01-crashloop-bad-config` — check pod status
2. `kubectl describe pod <pod-name>` — check Events section for exit code / reason
3. `kubectl logs <pod-name> --previous` — read the last crash output
4. `kubectl get configmap scenario-01-config -o yaml` — inspect the config values
5. Fix the ConfigMap and restart the Deployment

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- Pod `reason: CrashLoopBackOff` in pod status
- `Exit Code: 1` in container state
- Log lines starting with `FATAL:` indicating configuration errors
- High `restartCount` on the container
