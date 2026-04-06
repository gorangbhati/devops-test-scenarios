# Scenario 15: Network Policy Blocking Traffic – Service Communication Failure

## Overview

This scenario demonstrates a Kubernetes networking issue where a **NetworkPolicy**
prevents communication between two services in the same namespace.

The application consists of two components:

- **Frontend service (Node.js)** – makes an HTTP request to the backend
- **Backend service (Node.js)** – provides a simple API endpoint

A NetworkPolicy is configured to **deny all incoming traffic to the backend
pods**, which blocks communication from the frontend service.

## What Happens

The frontend application attempts to send a request to the backend service:

```
http://scenario-15-backend:8080
```

However, the NetworkPolicy (`k8s/networkpolicy.yaml`) blocks all incoming
traffic to the backend pods.

Because of this restriction:

- The backend service is running
- The frontend service is running
- Network communication between them is blocked

| Component | Behavior |
|----------|----------|
| Backend | Running normally |
| Frontend | Attempts to call backend |
| NetworkPolicy | Blocks traffic to backend |
| Result | Frontend cannot reach backend |

## Directory Structure

```
15-network-policy-block/
├── backend/
│   └── app/
│       ├── app.js           # Backend Node.js API
│       ├── package.json
│       └── Dockerfile
├── frontend/
│   └── app/
│       ├── app.js           # Frontend Node.js service calling backend
│       ├── package.json
│       └── Dockerfile
└── k8s/
    ├── backend.yaml        # Backend deployment and service
    ├── frontend.yaml       # Frontend deployment and service
    └── networkpolicy.yaml  # Network policy blocking backend traffic
```

## Reproducing the Scenario

Deploy the backend service:

```bash
kubectl apply -f k8s/backend.yaml
```

Deploy the frontend service:

```bash
kubectl apply -f k8s/frontend.yaml
```

Apply the network policy:

```bash
kubectl apply -f k8s/networkpolicy.yaml
```

Check the running pods:

```bash
kubectl get pods -n test-scenerios
```

Both services should be running.

## Observing the Failure

Execute a request from the frontend pod:

```bash
kubectl exec -it deployment/scenario-15-frontend -n test-scenerios -- wget -qO- http://scenario-15-backend:8080
```

Expected result:

```
connection timed out
```

or

```
Network error: cannot reach backend service
```

You can also verify that the backend pod is running:

```bash
kubectl get pods -n test-scenerios | grep scenario-15
```

Check the active network policies:

```bash
kubectl get networkpolicy -n test-scenerios
```

## Fixing the Scenario

Modify the NetworkPolicy to allow traffic from the frontend pods.

Example rule:

```yaml
ingress:
- from:
  - podSelector:
      matchLabels:
        app: frontend15
```

Reapply the updated policy:

```bash
kubectl apply -f k8s/networkpolicy.yaml
```

The frontend should now be able to communicate with the backend service.

## Troubleshooting Checklist

1. `kubectl get networkpolicy -n test-scenerios` — verify active policies  
2. `kubectl describe networkpolicy scenario-15-deny` — inspect policy rules  
3. `kubectl exec` into the frontend pod to test connectivity  
4. Verify labels used by NetworkPolicy selectors  

## Agentic Troubleshooting Signals

An autonomous troubleshooting agent should detect and act on:

- Service communication failures between pods
- NetworkPolicy resources affecting backend pods
- Connectivity timeouts between frontend and backend services
- Missing ingress rules allowing required traffic
