# Scenario 13: HPA Not Scaling – Missing Metrics Server

## Overview

This scenario demonstrates a Kubernetes autoscaling issue where a **Horizontal
Pod Autoscaler (HPA)** is configured but cannot scale the application because
the cluster lacks the **metrics server** required to provide CPU and memory
metrics.

Without resource metrics, the HPA cannot determine pod utilization and therefore
cannot perform scaling decisions.

## What Happens

The deployment (`k8s/deployment.yaml`) runs a simple Python application and an
HPA resource (`k8s/hpa.yaml`) attempts to scale the deployment based on CPU
utilization.

However, the cluster does not have the **metrics-server** installed or the
metrics API is unavailable. Because of this:

- The HPA cannot retrieve CPU utilization metrics
- The autoscaler cannot evaluate scaling conditions
- The number of replicas never changes

| Component | Behavior |
|----------|----------|
| Deployment | Runs the Python application |
| HPA | Configured to scale based on CPU usage |
| Metrics Server | Missing or unavailable |
| Result | Autoscaler cannot scale the deployment |

## Directory Structure

```
13-hpa-not-scaling/
├── app/
│   ├── app.py           # Python application generating CPU load
│   ├── requirements.txt
│   └── Dockerfile
└── k8s/
    ├── deployment.yaml  # Deployment with CPU resource requests
    └── hpa.yaml         # HorizontalPodAutoscaler configuration
```

## Reproducing the Scenario

Deploy the application:

```bash
kubectl apply -f k8s/deployment.yaml
```

Deploy the HPA resource:

```bash
kubectl apply -f k8s/hpa.yaml
```

Check the deployment:

```bash
kubectl get deployment -n test-scenerios
```

Check the autoscaler:

```bash
kubectl get hpa -n test-scenerios
```

## Observing the Failure

Describe the HPA resource:

```bash
kubectl describe hpa scenario-13-hpa -n test-scenerios
```

Expected message:

```
unable to get metrics for resource cpu:
no metrics returned from resource metrics API
```

You may also observe:

```
failed to get cpu utilization: missing metrics
```

Check the metrics API availability:

```bash
kubectl top pods -n test-scenerios
```

If the metrics server is missing, you will see:

```
error: Metrics API not available
```

## Fixing the Scenario

Install the Kubernetes metrics server:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Verify the metrics server is running:

```bash
kubectl get pods -n kube-system | grep metrics-server
```

Check metrics availability:

```bash
kubectl top pods -n test-scenerios
```

Once metrics are available, the HPA will begin scaling the deployment
automatically based on CPU utilization.

## Troubleshooting Checklist

1. `kubectl get hpa -n test-scenerios` — verify HPA resource exists  
2. `kubectl describe hpa scenario-13-hpa` — inspect autoscaler status  
3. `kubectl top pods` — confirm metrics availability  
4. Check if `metrics-server` is installed in the cluster  

## Agentic Troubleshooting Signals

An autonomous troubleshooting agent should detect and act on:

- HPA reporting **unknown metrics**
- Missing or unavailable metrics API
- Errors indicating **metrics server not installed**
- Autoscaler unable to compute CPU utilization
