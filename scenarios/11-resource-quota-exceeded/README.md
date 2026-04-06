# Scenario 11: Resource Quota Exceeded – Pod Creation Forbidden

## Overview

This scenario demonstrates a Kubernetes resource management issue where a
namespace has a **ResourceQuota** configured that enforces CPU and memory
resource requirements.

When a deployment attempts to create pods **without specifying resource
requests**, Kubernetes rejects the pod creation request. As a result, the
ReplicaSet fails to create pods and the deployment cannot progress.

## What Happens

The namespace contains a ResourceQuota named `scenario-11-quota` which requires
all pods to specify CPU and memory requests.

However, the deployment (`k8s/deployment.yaml`) intentionally omits these
resource requests. Because of this mismatch, Kubernetes denies the creation
of new pods.

| Component | Behavior |
|----------|----------|
| ResourceQuota | Requires CPU and memory requests |
| Deployment | Missing resource requests |
| Result | Pod creation is denied |

## Directory Structure

```
11-resource-quota-exceeded/
├── app/
│   ├── app.py           # Simple Python application
│   ├── requirements.txt
│   └── Dockerfile
└── k8s/
    ├── deployment.yaml  # Deployment missing resource requests
    └── quota.yaml       # ResourceQuota enforcing resource requirements
```

## Reproducing the Scenario

First apply the ResourceQuota:

```bash
kubectl apply -f k8s/quota.yaml
```

Then deploy the application:

```bash
kubectl apply -f k8s/deployment.yaml
```

Check deployment status:

```bash
kubectl get deployment -n test-scenerios
```

Check pods:

```bash
kubectl get pods -n test-scenerios
```

You will notice that **no pods are created**.

## Observing the Failure

Describe the deployment:

```bash
kubectl describe deployment scenario-11-resource-quota -n test-scenerios
```

Expected error message:

```
Error creating: pods "scenario-11-xxxxx" is forbidden:
failed quota: scenario-11-quota: must specify requests.cpu for: app;
requests.memory for: app
```

You can also inspect the ResourceQuota configuration:

```bash
kubectl describe resourcequota scenario-11-quota -n test-scenerios
```

## Fixing the Scenario

Edit the deployment to include CPU and memory requests:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "200m"
    memory: "256Mi"
```

Reapply the deployment:

```bash
kubectl apply -f k8s/deployment.yaml
```

Pods should now be created successfully.

## Troubleshooting Checklist

1. `kubectl get resourcequota -n test-scenerios` — verify quota exists  
2. `kubectl describe resourcequota scenario-11-quota` — inspect enforced limits  
3. `kubectl describe deployment scenario-11-resource-quota` — check failed pod creation events  
4. Ensure deployment defines `resources.requests` for CPU and memory  

## Agentic Troubleshooting Signals

An autonomous troubleshooting agent should detect and act on:

- ReplicaSet `FailedCreate` events
- Error messages indicating **quota violations**
- Missing CPU and memory requests in pod specifications
- ResourceQuota preventing pod creation
