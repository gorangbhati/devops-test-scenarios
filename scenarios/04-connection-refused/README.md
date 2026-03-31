# Scenario 04: Connection Refused to Internal Microservice

## Overview

This scenario demonstrates a common Kubernetes networking issue: **Service A cannot
connect to Service B** because the `BACKEND_URL` environment variable points to the
wrong port.  The backend service is perfectly healthy — the problem is purely in the
frontend's configuration.

## What Happens

Two services are deployed:

| Service | Role | Listens on |
|---------|------|-----------|
| `scenario-04-backend` | Returns JSON data | port **5000** |
| `scenario-04-frontend` | Proxies requests to backend | port **8080** |

The frontend's ConfigMap sets `BACKEND_URL: "http://scenario-04-backend:9999"` — the
**wrong port**. Every call to `GET /api/proxy` results in a TCP connection-refused
error, and the frontend returns HTTP 502 with a descriptive JSON error body.

## Directory Structure

```
04-connection-refused/
├── backend/app/
│   ├── main.py       # Backend: simple JSON API
│   └── Dockerfile
├── frontend/app/
│   ├── main.py       # Frontend: proxies to backend via BACKEND_URL
│   └── Dockerfile
├── k8s/
│   ├── backend-configmap.yaml
│   ├── frontend-configmap.yaml   # BUG: wrong BACKEND_URL port
│   ├── deployments.yaml          # Both deployments
│   └── services.yaml             # Both services
└── tests/
    └── test_services.py          # pytest tests
```

## Reproducing the Scenario

```bash
# Apply all manifests
kubectl apply -f k8s/backend-configmap.yaml
kubectl apply -f k8s/frontend-configmap.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml

# Wait for pods to be ready
kubectl rollout status deployment/scenario-04-backend
kubectl rollout status deployment/scenario-04-frontend

# Port-forward the frontend
kubectl port-forward svc/scenario-04-frontend 8080:80

# Hit the proxy endpoint — expect HTTP 502
curl -si http://localhost:8080/api/proxy
# HTTP/1.1 502 ...
# {"error": "Connection refused", "backend_url": "http://scenario-04-backend:9999", ...}
```

Backend is healthy:
```bash
kubectl port-forward svc/scenario-04-backend 5000:5000
curl -s http://localhost:5000/api/data
# {"source": "backend", "status": "healthy", ...}
```

## Checking the Logs

```bash
# Frontend logs show connection errors
kubectl logs -l app=scenario-04-frontend
# 2026-... ERROR Connection refused to backend at http://scenario-04-backend:9999

# Backend logs — no requests received (confirms it's a frontend config issue)
kubectl logs -l app=scenario-04-backend
```

## Fixing the Scenario

Edit `k8s/frontend-configmap.yaml`:
```yaml
data:
  BACKEND_URL: "http://scenario-04-backend:5000"  # correct port
```

Re-apply and restart:
```bash
kubectl apply -f k8s/frontend-configmap.yaml
kubectl rollout restart deployment/scenario-04-frontend
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- HTTP 502 responses from the frontend service
- Frontend pod logs containing `Connection refused` errors with the target URL
- No corresponding incoming requests in the backend pod logs
- `BACKEND_URL` value in the frontend ConfigMap pointing to an unreachable port
- `kubectl exec` from the frontend pod: `wget -qO- http://scenario-04-backend:9999` fails
