# Scenario 06: TLS Handshake Failure – Wrong Secret in Ingress

## Overview

This scenario demonstrates a common Kubernetes misconfiguration where an
Ingress resource references a **TLS secret that does not exist** in the
namespace.

Because the secret is missing, the ingress controller cannot configure HTTPS
correctly, which results in TLS configuration errors and failed HTTPS setup.

## What Happens

The Ingress configuration (`k8s/ingress.yaml`) specifies a TLS secret named
`invalid-tls-secret`.

| Field | Value |
|------|------|
| Host | `tls-scenario.local` |
| TLS Secret | `invalid-tls-secret` |

Since the secret does not exist in the namespace:

- The ingress controller fails to configure TLS
- Kubernetes generates warning events
- HTTPS traffic cannot be properly configured

## Directory Structure

```
06-tls-ingress-failure/
├── app/
│   ├── app.js           # Simple Node.js web server
│   ├── package.json
│   └── Dockerfile
└── k8s/
    ├── deployment.yaml  # Application deployment
    ├── service.yaml     # Service exposing the application
    └── ingress.yaml     # Ingress referencing a missing TLS secret
```

## Reproducing the Scenario

Deploy the application:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Apply the ingress configuration:

```bash
kubectl apply -f k8s/ingress.yaml
```

Check ingress resources:

```bash
kubectl get ingress -n test-scenerios
```

## Observing the Failure

Describe the ingress resource:

```bash
kubectl describe ingress scenario-06-ingress -n test-scenerios
```

Expected error:

```
Error syncing to GCP: error initializing translator env:
secrets "invalid-tls-secret" not found
```

You may also observe warnings such as:

```
Translation failed: invalid ingress spec
```

## Fixing the Scenario

Create the missing TLS secret:

```bash
kubectl create secret tls invalid-tls-secret \
  --cert=tls.crt \
  --key=tls.key \
  -n test-scenerios
```

Reapply the ingress:

```bash
kubectl apply -f k8s/ingress.yaml
```

The ingress controller should now configure TLS successfully.

## Troubleshooting Checklist

1. `kubectl get ingress -n test-scenerios` — verify ingress resource  
2. `kubectl describe ingress scenario-06-ingress` — inspect ingress events  
3. `kubectl get secrets -n test-scenerios` — confirm TLS secret exists  
4. Check ingress controller logs for TLS configuration errors  

## Agentic Troubleshooting Signals

An autonomous troubleshooting agent should detect and act on:

- Ingress controller sync failures
- Events indicating `secret not found`
- Missing TLS secret referenced by ingress
- TLS configuration errors for the ingress host
