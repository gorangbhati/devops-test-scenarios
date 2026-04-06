# Scenario 12: Rolling Update Stuck – Unhealthy New Version

## Overview

This scenario demonstrates a Kubernetes deployment issue where a **rolling
update becomes stuck** because the new version of the application never
becomes ready.

Kubernetes uses readiness probes to determine if a container is ready to serve
traffic. When the readiness probe continuously fails, the deployment cannot
progress and the rollout remains incomplete.

## What Happens

The deployment (`k8s/deployment.yaml`) performs a rolling update with two
replicas. The Node.js application intentionally fails the readiness probe by
returning a **500 status code** on the `/ready` endpoint.

Because the new pods never become ready:

- Kubernetes cannot mark them as available
- The rolling update cannot progress
- The deployment rollout remains stuck

| Component | Behavior |
|----------|----------|
| Deployment | Rolling update strategy |
| Readiness Probe | Always fails |
| Result | Deployment rollout stuck |

## Directory Structure

```
12-rolling-update-stuck/
├── app/
│   ├── app.js           # Node.js application with failing readiness probe
│   ├── package.json
│   └── Dockerfile
└── k8s/
    └── deployment.yaml  # Deployment with readiness and liveness probes
```

## Reproducing the Scenario

Deploy the application:

```bash
kubectl apply -f k8s/deployment.yaml
```

Check the deployment status:

```bash
kubectl get deployment -n test-scenerios
```

Check pods:

```bash
kubectl get pods -n test-scenerios
```

You will see pods running but not ready.

Example output:

```
scenario-12-rolling-update-xxxxx   0/1   Running
```

## Observing the Failure

Describe the deployment:

```bash
kubectl describe deployment scenario-12-rolling-update -n test-scenerios
```

The rollout will not complete.

Check rollout status:

```bash
kubectl rollout status deployment scenario-12-rolling-update -n test-scenerios
```

You may see:

```
Waiting for deployment "scenario-12-rolling-update" rollout to finish
```

Inspect the pod readiness failures:

```bash
kubectl describe pod <pod-name> -n test-scenerios
```

Expected message:

```
Readiness probe failed: HTTP probe failed with statuscode: 500
```

## Fixing the Scenario

Update the application so that the `/ready` endpoint returns a successful
response.

Example fix:

```javascript
app.get("/ready", (req, res) => {
  res.status(200).send("READY");
});
```

Rebuild and redeploy the updated image:

```bash
kubectl rollout restart deployment scenario-12-rolling-update -n test-scenerios
```

The deployment rollout should now complete successfully.

## Troubleshooting Checklist

1. `kubectl get deployment -n test-scenerios` — check rollout progress  
2. `kubectl rollout status deployment scenario-12-rolling-update` — verify rollout status  
3. `kubectl describe pod <pod-name>` — inspect readiness probe failures  
4. Verify the application readiness endpoint returns HTTP 200  

## Agentic Troubleshooting Signals

An autonomous troubleshooting agent should detect and act on:

- Deployment rollout stuck in progress
- Pods in `Running` state but **not Ready**
- Repeated readiness probe failures
- HTTP 500 responses from readiness endpoint
