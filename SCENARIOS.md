# Kubernetes Test Scenarios

This repository contains test applications and Kubernetes manifests designed for autonomous agentic troubleshooting of common Kubernetes issues.

## Scenarios

| # | Scenario | Status | App Language | Directory |
|---|----------|--------|--------------|-----------|
| 01 | [CrashLoop due to Bad Config](#01-crashloop-due-to-bad-config) | ✅ Implemented | Python | `scenarios/01-crashloop-bad-config/` |
| 02 | [API Latency – N+1 Database Queries](#02-api-latency--n1-database-queries) | ✅ Implemented | Node.js | `scenarios/02-api-latency-n-plus-one/` |
| 03 | [Container OOMKilled – Memory Leak](#03-container-oomkilled--memory-leak) | ✅ Implemented | Go | `scenarios/03-oomkilled-memory-leak/` |
| 04 | [Connection Refused to Internal Microservice](#04-connection-refused-to-internal-microservice) | ✅ Implemented | Python | `scenarios/04-connection-refused/` |
| 05 | [PVC Stuck in Pending](#05-pvc-stuck-in-pending) | ✅ Implemented | Python | `scenarios/05-pvc-pending/` |
| 06 | [TLS Handshake Failures – Wrong Secret in Ingress](#06-tls-handshake-failures--wrong-secret-in-ingress) | ✅ Implemented | Node.js | `scenarios/06-tls-ingress-failure/` |
| 07 | [Pods Can't Resolve DNS](#07-pods-cant-resolve-dns) | ✅ Implemented | Python | `scenarios/07-dns-resolution-failure/` |
| 08 | [Pods Stuck in Pending – Scheduler Failures](#08-pods-stuck-in-pending--scheduler-failures) | ✅ Implemented | Python | `scenarios/08-pods-pending-scheduler/` |
| 09 | [ImagePullBackOff – Bad Image / Missing Credentials](#09-imagepullbackoff--bad-image--missing-credentials) | ✅ Implemented | k8s manifests | `scenarios/09-imagepullbackoff/` |
| 10 | [Liveness Probe Failure – App Deadlock](#10-liveness-probe-failure--app-deadlock) | ✅ Implemented | Go | `scenarios/10-liveness-probe-failure/` |
| 11 | [Resource Quota Exceeded](#11-resource-quota-exceeded) | ✅ Implemented | Python | `scenarios/11-resource-quota-exceeded/` |
| 12 | [Rolling Update Stuck – Unhealthy New Version](#12-rolling-update-stuck--unhealthy-new-version) | ✅ Implemented | Node.js | `scenarios/12-rolling-update-stuck/` |
| 13 | [HPA Not Scaling – Missing Metrics Server](#13-hpa-not-scaling--missing-metrics-server) | ✅ Implemented | Python | `scenarios/13-hpa-not-scaling/` |
| 14 | [Secret Not Mounted – App Fails to Start](#14-secret-not-mounted--app-fails-to-start) | ✅ Implemented | Python | `scenarios/14-secret-not-mounted/` |
| 15 | [Network Policy Blocking Traffic](#15-network-policy-blocking-traffic) | ✅ Implemented | Node.js | `scenarios/15-network-policy-block/` |
| 16 | [Background Goroutine Panic – Empty Slice Out-of-Bounds](#16-background-goroutine-panic--empty-slice-out-of-bounds) | ✅ Implemented | Go | `scenarios/16-background-goroutine-panic/` |
| 17 | [Checkout 500 – Unhandled KeyError on Uppercase Region](#17-checkout-500--unhandled-keyerror-on-uppercase-region) | ✅ Implemented | Python | `scenarios/17-unhandled-exception-checkout/` |

---

## Scenario Details

### 01: CrashLoop due to Bad Config

**Problem:** The application reads required configuration from environment variables at startup. If any required variable is missing or has an invalid value, the process exits with a non-zero code, causing Kubernetes to enter a `CrashLoopBackOff` state.

**Symptoms:**
- Pod status shows `CrashLoopBackOff`
- `kubectl logs <pod>` shows a configuration error message
- Restart count increases over time

**Root Cause:** ConfigMap is missing required keys or contains invalid values (e.g., a non-numeric port, an unparseable database URL).

**Resolution:** Fix the ConfigMap with valid values and re-apply.

---

### 02: API Latency – N+1 Database Queries

**Problem:** A REST API endpoint fetches a list of records and then makes individual queries for each record instead of a single JOIN query, causing high latency under load.

**Symptoms:**
- High p99 latency on the `/items` endpoint
- Database shows many small repeated queries
- APM traces show hundreds of DB spans per request

**Root Cause:** ORM lazy-loading triggers one query per object in a loop (N+1 pattern).

**Resolution:** Replace lazy loading with an eager/batch query.

---

### 03: Container OOMKilled – Memory Leak

**Problem:** The application leaks memory over time (e.g., caching objects in a global list without eviction). The container exceeds its memory limit and is killed by the OOM killer.

**Symptoms:**
- Pod restarts with reason `OOMKilled`
- Container memory usage grows monotonically until killed
- `kubectl describe pod` shows `Last State: Terminated, Reason: OOMKilled`

**Root Cause:** Application holds unbounded references to data in memory.

**Resolution:** Fix the memory leak or increase the memory limit.

---

### 04: Connection Refused to Internal Microservice

**Problem:** Service A tries to call Service B using a wrong hostname or port. The TCP connection is refused, returning HTTP 500 errors to clients.

**Symptoms:**
- Errors in logs: `Connection refused` or `dial tcp: connect: connection refused`
- HTTP 500 responses from Service A
- Service B is running and healthy

**Root Cause:** Incorrect `SERVICE_B_URL` environment variable (wrong port or hostname typo).

**Resolution:** Correct the service URL in the ConfigMap.

---

### 05: PVC Stuck in Pending

**Problem:** A PersistentVolumeClaim is created but no PersistentVolume can satisfy it — either due to no matching storage class, insufficient capacity, or access mode mismatch.

**Symptoms:**
- `kubectl get pvc` shows `Pending` status indefinitely
- Pods that depend on the PVC are also stuck in `Pending`
- `kubectl describe pvc` shows no matching PV

**Root Cause:** PVC requests a non-existent StorageClass or more storage than available.

**Resolution:** Create a matching PV or correct the StorageClass name.

---

### 06: TLS Handshake Failures – Wrong Secret in Ingress

**Problem:** The Ingress resource references a TLS secret that does not exist or contains invalid certificates, causing TLS handshake failures for all HTTPS clients.

**Symptoms:**
- Browser shows `SSL_ERROR_RX_RECORD_TOO_LONG` or certificate error
- `curl -v` shows TLS handshake failure
- Ingress controller logs show secret not found

**Root Cause:** `spec.tls[].secretName` in the Ingress references a non-existent or incorrectly named secret.

**Resolution:** Create the correct TLS secret or fix the Ingress `secretName`.

---

### 07: Pods Can't Resolve DNS

**Problem:** Application pods cannot resolve internal Kubernetes service names or external hostnames, causing all outbound connections to fail.

**Symptoms:**
- Application logs show `Name or service not known` errors
- `kubectl exec <pod> -- nslookup kubernetes.default` fails
- CoreDNS pods may be unhealthy or missing

**Root Cause:** CoreDNS ConfigMap is misconfigured (e.g., wrong upstream resolvers), or CoreDNS pods are not running.

**Resolution:** Restore the correct CoreDNS ConfigMap and ensure CoreDNS pods are running.

---

### 08: Pods Stuck in Pending – Scheduler Failures

**Problem:** Pods remain in `Pending` state because no node satisfies their scheduling constraints: node selectors, tolerations, or resource requests that exceed available capacity.

**Symptoms:**
- `kubectl get pods` shows `Pending` for extended time
- `kubectl describe pod` shows `FailedScheduling` events
- Events indicate `Insufficient memory`, `Insufficient cpu`, or `node(s) didn't match node selector`

**Root Cause:** Pod spec requests more resources than any node can provide, or uses a node selector with no matching nodes.

**Resolution:** Reduce resource requests, remove incorrect node selectors, or add tolerations.

---

### 09: ImagePullBackOff – Bad Image / Missing Credentials

**Problem:** Kubernetes cannot pull the specified container image because the image name is wrong, the tag does not exist, or the imagePullSecret is missing/invalid for a private registry.

**Symptoms:**
- Pod status shows `ImagePullBackOff` or `ErrImagePull`
- `kubectl describe pod` shows `Failed to pull image`
- Events mention `unauthorized` or `not found`

**Root Cause:** Typo in image name/tag, or missing `imagePullSecrets` for a private registry.

**Resolution:** Correct the image name/tag or create and reference the correct imagePullSecret.

---

### 10: Liveness Probe Failure – App Deadlock

**Problem:** The application enters a deadlock or infinite loop in its request-handling goroutine/thread. The HTTP server stops responding. The liveness probe fails, and Kubernetes restarts the container repeatedly.

**Symptoms:**
- Pod restarts regularly (visible in `RESTARTS` column)
- Liveness probe failure events in `kubectl describe pod`
- Container logs show normal startup followed by silence

**Root Cause:** A mutex or goroutine deadlock causes the health endpoint to stop responding.

**Resolution:** Fix the deadlock or temporarily disable the faulty code path.

---

### 11: Resource Quota Exceeded

**Problem:** A namespace has a ResourceQuota configured. When a new Deployment is created, it would exceed the allowed CPU or memory quota, causing pod creation to be rejected.

**Symptoms:**
- `kubectl get pods` shows no new pods
- `kubectl describe replicaset` shows `exceeded quota` error
- Existing pods continue running

**Root Cause:** Namespace ResourceQuota is too restrictive for the new workload.

**Resolution:** Increase the quota or reduce the resource requests of the new Deployment.

---

### 12: Rolling Update Stuck – Unhealthy New Version

**Problem:** A new version of the application fails its readiness probe (e.g., the new image has a bug that prevents the `/ready` endpoint from returning 200). The rolling update stalls because it waits for the new pod to become ready before terminating old pods.

**Symptoms:**
- `kubectl rollout status deployment/<name>` hangs
- Mix of old and new pod versions running
- New pods show `0/1 Ready`

**Root Cause:** The new container image fails its readiness check.

**Resolution:** Roll back (`kubectl rollout undo`) and fix the application bug.

---

### 13: HPA Not Scaling – Missing Metrics Server

**Problem:** A HorizontalPodAutoscaler is configured to scale on CPU utilization, but the Metrics Server is not installed in the cluster, so the HPA cannot fetch metrics and remains in an error state.

**Symptoms:**
- `kubectl get hpa` shows `<unknown>/50%` for CPU
- HPA events show `unable to get metrics for resource cpu`
- Pods do not scale despite high load

**Root Cause:** Metrics Server is not installed or is unhealthy.

**Resolution:** Install the Metrics Server Helm chart or apply its manifests.

---

### 14: Secret Not Mounted – App Fails to Start

**Problem:** The Deployment references a Kubernetes Secret (e.g., for a database password) that does not exist. The pod fails to start because the secret volume cannot be mounted.

**Symptoms:**
- Pod stuck in `ContainerCreating` or `Pending`
- `kubectl describe pod` shows `MountVolume.SetUp failed`
- Event: `secret "<name>" not found`

**Root Cause:** The referenced Secret was not created before the Deployment, or it was deleted.

**Resolution:** Create the missing Secret with the correct name and data.

---

### 15: Network Policy Blocking Traffic

**Problem:** A NetworkPolicy restricts ingress/egress traffic in a namespace. A new service is deployed without updating the NetworkPolicy, so all traffic to it is silently dropped.

**Symptoms:**
- Service is reachable within the same pod but not from other pods/namespaces
- No TCP connection errors — connections just time out
- Other services in the same namespace work fine

**Root Cause:** A default-deny NetworkPolicy is active and the new service has no matching allow rule.

**Resolution:** Add an appropriate NetworkPolicy rule to allow traffic to the new service.

---

### 16: Background Goroutine Panic – Empty Slice Out-of-Bounds

**Problem:** A Go game-score service runs a background goroutine that periodically computes aggregate statistics (min, max, average). The `computeStats` helper accesses `scores[0]` and `scores[n-1]` without guarding against an empty slice. The HTTP handler for `/api/scores/stats` has the empty-store guard, but the goroutine does not. After a season reset (`DELETE /api/scores`) the next background tick panics:

```
panic: runtime error: index out of range [0] with length 0
```

Because the panic occurs in a goroutine started from `main()` — not an HTTP handler goroutine — `net/http`'s built-in recovery does not apply and the process exits.

**Symptoms:**
- Pod enters `CrashLoopBackOff` roughly `STATS_INTERVAL_SEC` seconds after the season reset
- `kubectl logs --previous` shows the panic stack trace pointing to `computeStats` → `statsLoop`
- `GET /api/scores/stats` responds correctly (`{"count":0}`) before the crash — misleading responders into thinking the code handles empty stores
- Pod restarts fine (re-seeds scores) but crashes again if reset is triggered

**Root Cause:** `computeStats` assumes a non-empty input slice; the background goroutine calls it unconditionally. Test runs completed before the 30-second background tick, so the path was never exercised.

**Resolution:** Add `if len(scores) == 0 { continue }` in `statsLoop`, or add the guard inside `computeStats` itself.

---

### 17: Checkout 500 – Unhandled KeyError on Uppercase Region

**Problem:** A Python Flask checkout service stores tax rates in a dict keyed by lowercase region codes (`"us"`, `"eu"`, etc.). The `_get_tax_rate()` helper does a plain dict lookup without normalising the input to lowercase. When a mobile-app update starts sending uppercase region codes (`"US"`, `"EU"`, etc.), the lookup raises a `KeyError`. The checkout handler catches `ValueError` and `TypeError` for item validation, but not `KeyError` — Flask converts it to HTTP 500 for every affected request.

**Symptoms:**
- HTTP 500 error rate spikes on `POST /api/checkout`; pod stays alive (no restarts)
- `kubectl logs` shows repeated `KeyError: 'US'` tracebacks pointing to `_get_tax_rate` → `TAX_RATES[region]`
- Errors affect only mobile-app clients (after the update); web clients using lowercase codes are unaffected
- Liveness/readiness probes continue to pass

**Root Cause:** Missing `.lower()` normalisation in `_get_tax_rate`. QA always used lowercase region codes matching the API spec; the mobile-app change to uppercase reached production after the test cycle.

**Resolution:** Normalise the region code before the dict lookup — `TAX_RATES[region.lower()]` — and raise a descriptive `ValueError` for truly unsupported regions.

---

## GCP Deployment Configuration

### Required GitHub Secrets

| Secret Name | Description |
|-------------|-------------|
| `GCP_PROJECT_ID` | GCP project ID where the GKE cluster lives |
| `GCP_SA_KEY` | Base64-encoded JSON key of a GCP Service Account with roles: `roles/container.developer`, `roles/artifactregistry.writer` |
| `GKE_CLUSTER_NAME` | Name of the GKE cluster |
| `GKE_CLUSTER_ZONE` | Zone or region of the GKE cluster (e.g., `us-central1-a`) |
| `GAR_LOCATION` | Artifact Registry location (e.g., `us-central1`) |
| `GAR_REPOSITORY` | Artifact Registry repository name (e.g., `devops-test-scenarios`) |

### GCP Service Account Roles Required

```
roles/container.developer      # Deploy to GKE
roles/artifactregistry.writer  # Push images to Artifact Registry
roles/iam.serviceAccountUser   # Impersonate service account if needed
```

### Artifact Registry Setup

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create devops-test-scenarios \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for k8s test scenarios"

# Configure Docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### GKE Cluster Access

```bash
# Get cluster credentials
gcloud container clusters get-credentials <CLUSTER_NAME> \
  --zone <CLUSTER_ZONE> \
  --project <PROJECT_ID>
```
