# devops-test-scenarios

A collection of test applications and Kubernetes manifests designed for autonomous agentic troubleshooting of common Kubernetes issues.

## Quick Start

Each scenario lives in its own directory under `scenarios/` and is self-contained:

```
scenarios/
├── 01-crashloop-bad-config/       # CrashLoopBackOff caused by invalid env vars (Python)
├── 02-api-latency-n-plus-one/     # High latency from N+1 database queries (Node.js)
├── 03-oomkilled-memory-leak/      # OOMKilled container from unbounded memory leak (Go)
├── 04-connection-refused/         # 502 errors from wrong internal service URL (Python)
├── 05-pvc-pending/                # Pod Pending due to non-existent StorageClass (Python)
├── 07-dns-resolution-failure/     # DNS failures from broken CoreDNS config (Python)
├── 08-pods-pending-scheduler/     # Pod Pending from impossible nodeSelector + resources (Python)
├── 09-imagepullbackoff/           # ImagePullBackOff: bad image name or missing pull secret (k8s)
└── 10-liveness-probe-failure/     # Liveness probe timeouts from app mutex deadlock (Go)
```

See [SCENARIOS.md](SCENARIOS.md) for the full list of scenarios and GCP deployment configuration.

## GCP Deployment Prerequisites

Configure the following GitHub repository secrets before running any workflow:

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_SA_KEY` | Base64-encoded GCP service account JSON key |
| `GKE_CLUSTER_NAME` | GKE cluster name |
| `GKE_CLUSTER_ZONE` | GKE cluster zone (e.g. `us-central1-a`) |
| `GAR_LOCATION` | Artifact Registry location (e.g. `us-central1`) |
| `GAR_REPOSITORY` | Artifact Registry repository name |
