# Scenario 14: Secret Not Mounted – Application Fails to Start

## Overview

This scenario demonstrates a common Kubernetes configuration issue where an
application depends on a **Kubernetes Secret** for configuration, but the secret
is not mounted correctly in the pod.

Because the required secret is missing, the application cannot read the
necessary configuration and fails during startup.

## What Happens

The Python application (`app/app.py`) expects a secret value to be available as
an environment variable or mounted file.

However, the deployment (`k8s/deployment.yaml`) references a secret that does
not exist in the namespace. As a result:

- Kubernetes attempts to start the container
- The application cannot access the required secret
- The container exits with an error
- The pod repeatedly restarts

| Component | Behavior |
|----------|----------|
| Deployment | References a secret |
| Secret | Missing or not mounted |
| Application | Fails to start |
| Result | Pod enters CrashLoopBackOff |

## Directory Structure

```
14-secret-not-mounted/
├── app/
│   ├── app.py           # Python application expecting a secret value
│   ├── requirements.txt
│   └── Dockerfile
└── k8s/
    └── deployment.yaml  # Deployment referencing a missing secret
```

## Reproducing the Scenario

Deploy the application:

```bash
kubectl apply -f k8s/deployment.yaml
```

Check pod status:

```bash
kubectl get pods -n test-scenerios
```

You will observe the pod restarting repeatedly.

Example:

```
scenario-14-secret-xxxxx   0/1   CrashLoopBackOff
```

## Observing the Failure

Describe the pod:

```bash
kubectl describe pod <pod-name> -n test-scenerios
```

Check container logs:

```bash
kubectl logs <pod-name> -n test-scenerios
```

Expected error message:

```
Error: required secret not found
```

or

```
Environment variable SECRET_KEY is not set
```

You can also confirm the secret is missing:

```bash
kubectl get secrets -n test-scenerios
```

The required secret will not appear in the list.

## Fixing the Scenario

Create the required Kubernetes secret:

```bash
kubectl create secret generic scenario-14-secret \
  --from-literal=SECRET_KEY=my-secret-value \
  -n test-scenerios
```

Redeploy or restart the application:

```bash
kubectl rollout restart deployment scenario-14-secret -n test-scenerios
```

Once the secret is available, the application will start successfully.

## Troubleshooting Checklist

1. `kubectl get secrets -n test-scenerios` — verify secret exists  
2. `kubectl describe pod <pod-name>` — inspect startup errors  
3. `kubectl logs <pod-name>` — check application logs  
4. Ensure deployment correctly references the secret  

## Agentic Troubleshooting Signals

An autonomous troubleshooting agent should detect and act on:

- Pod `CrashLoopBackOff` status
- Application startup failures
- Missing secret referenced by deployment
- Environment variables or volumes referencing non-existent secrets
