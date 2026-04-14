# devops-test-scenarios

A collection of test applications and Kubernetes manifests designed for autonomous agentic troubleshooting of common Kubernetes issues.

## Quick Start

Each scenario lives in its own directory under `scenarios/` and is self-contained:

```
scenarios/
├── 01-crashloop-bad-config/        # CrashLoopBackOff caused by invalid env vars (Python)
├── 02-api-latency-n-plus-one/      # High latency from N+1 database queries (Node.js)
├── 03-oomkilled-memory-leak/       # OOMKilled container from unbounded memory leak (Go)
├── 04-connection-refused/          # 502 errors from wrong internal service URL (Python)
├── 05-pvc-pending/                 # Pod Pending due to non-existent StorageClass (Python)
├── 06-cpu-throttling/              # High latency caused by CPU limits throttling container
├── 07-dns-resolution-failure/      # DNS failures from broken CoreDNS config (Python)
├── 08-pods-pending-scheduler/      # Pod Pending from impossible nodeSelector + resources (Python)
├── 09-imagepullbackoff/            # ImagePullBackOff: bad image name or missing pull secret (k8s)
├── 10-liveness-probe-failure/      # Liveness probe timeouts from app mutex deadlock (Go)
├── 11-service-port-mismatch/       # Service unreachable due to incorrect targetPort
├── 12-configmap-not-loaded/        # Application fails because ConfigMap values not mounted
├── 13-ingress-routing-error/       # 404 errors due to incorrect ingress routing rules
├── 14-secret-not-mounted/          # Application fails because required Secret not mounted
├── 15-readiness-probe-failure/     # Pod never becomes Ready due to failing readiness probe
├── 16-background-goroutine-panic/  # CrashLoopBackOff: background goroutine panics on empty slice (Go)
└── 17-unhandled-exception-checkout/ # HTTP 500: unhandled KeyError on uppercase region code (Python)
```

See [SCENARIOS.md](SCENARIOS.md) for the full list of scenarios and GCP deployment configuration.

## GCP Deployment Prerequisites

Configure the following GitHub repository variables and secrets before running any workflow:

**Repository Variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Description |
|----------|-------------|
| `PROJECT_ID` | GCP project ID |
| `CLUSTER_NAME` | GKE cluster name |

**Repository / Organization Secrets** (Settings → Secrets and variables → Actions → Secrets):

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | Base64-encoded GCP service account JSON key |
| `GHCR_PAT` | GitHub Personal Access Token with `write:packages` scope (for pushing images to GHCR) |

Images are built and pushed to GitHub Container Registry (`ghcr.io`). The GKE cluster location is resolved automatically at deploy time via `gcloud container clusters list`.
