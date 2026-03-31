# devops-test-scenarios

A collection of test applications and Kubernetes manifests designed for autonomous agentic troubleshooting of common Kubernetes issues.

## Quick Start

Each scenario lives in its own directory under `scenarios/` and is self-contained:

```
scenarios/
└── 01-crashloop-bad-config/   # CrashLoopBackOff caused by invalid env vars
    ├── app/                   # Python application + Dockerfile
    ├── k8s/                   # Kubernetes manifests (ConfigMap + Deployment)
    ├── tests/                 # Unit tests
    └── README.md              # Scenario-specific instructions
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
