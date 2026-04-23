# DevOps Test Scenarios

A collection of **Kubernetes troubleshooting scenarios** designed for practicing and evaluating **DevOps debugging skills** and **autonomous agent troubleshooting**.

Each scenario intentionally introduces a **real-world production issue** such as:

- CrashLoopBackOff
- ImagePullBackOff
- OOMKilled
- DNS failures
- Service misconfiguration
- Broken ingress routing
- Resource quota issues
- Network policy restrictions

These scenarios help practice **observability, debugging, and root-cause analysis in Kubernetes environments**.

---

# Repository Structure

```
scenarios/
├── 01-crashloop-bad-config/
├── 02-api-latency-n-plus-one/
├── 03-oomkilled-memory-leak/
├── 04-connection-refused/
├── 05-pvc-pending/
├── 06-cpu-throttling/
├── 07-dns-resolution-failure/
├── 08-pods-pending-scheduler/
├── 09-imagepullbackoff/
├── 10-liveness-probe-failure/
├── 11-service-port-mismatch/
├── 12-configmap-not-loaded/
├── 13-ingress-routing-error/
├── 14-secret-not-mounted/
├── 15-readiness-probe-failure/
├── 16-background-goroutine-panic/
└── 17-unhandled-exception-checkout/
```

Each scenario contains:

```
app/        → application code
k8s/        → Kubernetes manifests
tests/      → optional unit tests
workflow    → GitHub Actions deployment pipeline
```

---

# GCP Deployment Prerequisites

Before running the workflows, configure the following in your repository.

### Repository Variables
(Settings → Secrets and variables → Actions → Variables)

| Variable | Description |
|--------|-------------|
| `PROJECT_ID` | Google Cloud project ID |
| `CLUSTER_NAME` | GKE cluster name |

---

### Repository Secrets
(Settings → Secrets and variables → Actions → Secrets)

| Secret | Description |
|------|-------------|
| `GCP_SA_KEY` | Base64 encoded GCP Service Account key |
| `GHCR_PAT` | GitHub token with `write:packages` permission |

---

# How Deployment Works

Each scenario workflow performs the following steps:

```
1️⃣ Lint / Unit tests
2️⃣ Build Docker image
3️⃣ Push image to GHCR
4️⃣ Authenticate with GCP
5️⃣ Get GKE credentials
6️⃣ Create namespace
7️⃣ Deploy Kubernetes manifests
```

Images are stored in:

```
ghcr.io/<github-username>/<scenario-name>
```

---

# How to Run a Scenario

### Step 1 — Trigger workflow

Go to:

```
GitHub → Actions
```

Select the scenario workflow and click:

```
Run workflow
```

---

### Step 2 — Verify deployment

Check resources in the cluster:

```bash
kubectl get pods -n test-scenerios
kubectl get deployments -n test-scenerios
kubectl get svc -n test-scenerios
```

---

### Step 3 — Observe failure

Each scenario intentionally produces a **failure condition**.

Example:

```
CrashLoopBackOff
ImagePullBackOff
Pending Pods
HTTP 500 errors
High latency
```

---

### Step 4 — Investigate

Use standard Kubernetes debugging commands:

```bash
kubectl describe pod <pod>
kubectl logs <pod>
kubectl get events -n test-scenerios
kubectl describe deployment <deployment>
```

---

### Step 5 — Fix the issue

Update the misconfigured component:

Examples:

```
Fix ConfigMap values
Fix service port
Fix image name
Correct ingress routing
Fix resource limits
```

---

### Step 6 — Redeploy

After fixing the issue:

```
kubectl apply -f k8s/
```

or re-run the workflow.

---

# Scenario Overview

---

## Scenario 01 — CrashLoopBackOff (Bad Config)

**Issue**

Application crashes due to invalid environment variables.

**Root Cause**

ConfigMap contains invalid configuration.

Example problems:

```
DATABASE_URL uses wrong scheme
APP_PORT is not an integer
LOG_LEVEL unsupported
```

**Expected Symptom**

```
CrashLoopBackOff
```

---

## Scenario 02 — API Latency (N+1 Queries)

**Issue**

API endpoint becomes slow due to inefficient database queries.

**Root Cause**

Application performs **N+1 query pattern**.

**Expected Symptom**

```
High response latency
Slow API responses
```

---

### Accessing the API

Once the scenario is deployed, the service exposes the API.

Get the service IP:

kubectl get svc -n test-scenerios

Example output:

scenario-02-service   LoadBalancer   34.xxx.xxx.xxx

Access the API:

http://<EXTERNAL-IP>/api/orders
http://<EXTERNAL-IP>/api/orders/optimized

## Scenario 03 — OOMKilled Memory Leak

**Issue**

Application continuously allocates memory.

**Root Cause**

Unbounded memory growth.

**Expected Symptom**

```
OOMKilled
Container restart loops
```

---

## Scenario 04 — Connection Refused

**Issue**

Frontend cannot communicate with backend.

**Root Cause**

Incorrect service URL or port.

**Expected Symptom**

```
HTTP 502
Connection refused
```

---

## Scenario 05 — PVC Pending

**Issue**

Pod stuck in Pending state.

**Root Cause**

Requested StorageClass does not exist.

**Expected Symptom**

```
Pod Pending
PVC Pending
```

---

## Scenario 06 — CPU Throttling

**Issue**

Application responds slowly.

**Root Cause**

CPU limit too restrictive.

**Expected Symptom**

```
High latency
CPU throttling
```

---

## Scenario 07 — DNS Resolution Failure

**Issue**

Application cannot resolve internal service names.

**Root Cause**

Broken CoreDNS configuration.

**Expected Symptom**

```
DNS lookup failures
```

---

## Scenario 08 — Scheduler Failure

**Issue**

Pods never get scheduled.

**Root Cause**

Impossible nodeSelector or resource request.

**Expected Symptom**

```
Pod Pending
```

---

## Scenario 09 — ImagePullBackOff

**Issue**

Container image cannot be pulled.

**Root Cause**

Incorrect image name or missing registry credentials.

**Expected Symptom**

```
ImagePullBackOff
```

---

## Scenario 10 — Liveness Probe Failure

**Issue**

Container repeatedly restarts.

**Root Cause**

Application deadlock prevents health check from responding.

**Expected Symptom**

```
Liveness probe failures
CrashLoopBackOff
```

---

## Scenario 11 — Service Port Mismatch

**Issue**

Service does not route traffic correctly.

**Root Cause**

Incorrect `targetPort`.

**Expected Symptom**

```
Service unreachable
```

---

## Scenario 12 — ConfigMap Not Loaded

**Issue**

Application fails because configuration values are missing.

**Root Cause**

ConfigMap not mounted or referenced.

**Expected Symptom**

```
Application startup failure
```

---

## Scenario 13 — Ingress Routing Error

**Issue**

Ingress returns 404 errors.

**Root Cause**

Incorrect ingress routing rule.

**Expected Symptom**

```
HTTP 404
```

---

## Scenario 14 — Secret Not Mounted

**Issue**

Application cannot access required credentials.

**Root Cause**

Secret missing or not mounted.

**Expected Symptom**

```
Startup failure
```

---

## Scenario 15 — Readiness Probe Failure

**Issue**

Pod never becomes ready.

**Root Cause**

Readiness probe always fails.

**Expected Symptom**

```
Pod not ready
Service not routing traffic
```

---

## Scenario 16 — Background Goroutine Panic

**Issue**

Application crashes due to background thread panic.

**Root Cause**

Unsafe slice access.

**Expected Symptom**

```
CrashLoopBackOff
```

---

## Scenario 17 — Unhandled Exception

**Issue**

Checkout API throws exception.

**Root Cause**

Unhandled key error when parsing region code.

**Expected Symptom**

```
HTTP 500 errors
```

---

# Useful Debug Commands

### View cluster resources

```bash
kubectl get all -n test-scenerios
```

---

### Describe pod

```bash
kubectl describe pod <pod-name>
```

---

### View logs

```bash
kubectl logs <pod-name>
```

---

### Check events

```bash
kubectl get events -n test-scenerios
```

---
