# Scenario 07: Pods Can't Resolve DNS

## Overview

This scenario demonstrates what happens when Kubernetes pods cannot resolve DNS names — typically caused by a **misconfigured CoreDNS** ConfigMap that routes DNS queries to an unreachable upstream resolver.

## What Happens

The Python application attempts to resolve the hostname specified in `UPSTREAM_HOST` on every `/dns-check` request. In a healthy cluster this succeeds; after applying the broken CoreDNS ConfigMap, DNS resolution fails with `SERVFAIL` or `Name or service not known` and the endpoint returns HTTP 503.

## Directory Structure

```
07-dns-resolution-failure/
├── app/
│   ├── main.py      # Python app with /dns-check endpoint
│   └── Dockerfile
├── k8s/
│   ├── configmap.yaml              # App config (UPSTREAM_HOST)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── broken-coredns-configmap.yaml  # Apply to BREAK DNS in the cluster
│   └── healthy-coredns-configmap.yaml # Apply to RESTORE DNS
└── tests/
    └── test_dns_check.py
```

## Reproducing the Scenario

### Step 1: Deploy the app (DNS works normally)

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl port-forward svc/scenario-07-dns-check 8080:80

# DNS resolves fine
curl -s http://localhost:8080/dns-check | jq
# { "resolved": true, "host": "kubernetes.default.svc.cluster.local", ... }
```

### Step 2: Break CoreDNS (triggers the scenario)

```bash
# ⚠️  WARNING: this breaks DNS for ALL pods in the cluster
kubectl apply -f k8s/broken-coredns-configmap.yaml
kubectl rollout restart deployment/coredns -n kube-system
sleep 10

curl -s http://localhost:8080/dns-check | jq
# { "resolved": false, "message": "DNS resolution failed ...", ... }
# HTTP 503
```

### Step 3: Diagnose

```bash
# Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Confirm broken upstream
kubectl exec -it $(kubectl get pod -l app=scenario-07 -o name | head -1) \
  -- python3 -c "import socket; print(socket.getaddrinfo('google.com', None))"
# socket.gaierror: [Errno -3] Temporary failure in name resolution
```

### Step 4: Fix

```bash
kubectl apply -f k8s/healthy-coredns-configmap.yaml
kubectl rollout restart deployment/coredns -n kube-system
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- HTTP 503 from `/dns-check` with `"resolved": false`
- App logs: `DNS resolution failed for 'kubernetes.default.svc.cluster.local'`
- `kubectl exec <pod> -- nslookup kubernetes.default` fails with `SERVFAIL`
- CoreDNS pod logs show `SERVFAIL` for all queries
- CoreDNS ConfigMap `forward` directive points to `192.0.2.1` (an unreachable TEST-NET address)
