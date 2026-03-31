# Scenario 09: ImagePullBackOff – Bad Image / Missing Credentials

## Overview

This scenario demonstrates two common causes of `ImagePullBackOff`:

1. **Bad image name** (`deployment-bad-image.yaml`) — the registry, repository, or tag simply does not exist.
2. **Missing imagePullSecret** (`deployment-missing-secret.yaml`) — the image lives in a private registry but the pod spec lacks an `imagePullSecrets` entry.

There is no custom application code for this scenario — the failure happens at the Kubernetes image-pull layer before a container even starts.

## Directory Structure

```
09-imagepullbackoff/
└── k8s/
    ├── deployment-bad-image.yaml      # image: non-existent-registry/app:v999
    └── deployment-missing-secret.yaml # real registry image, missing pull secret
```

## Reproducing the Scenario

### Variant A – Bad image name

```bash
kubectl apply -f k8s/deployment-bad-image.yaml

kubectl get pods -l scenario=09-imagepullbackoff
# NAME                          READY   STATUS             RESTARTS   AGE
# scenario-09-bad-image-xxx     0/1     ErrImagePull       0          15s
# scenario-09-bad-image-xxx     0/1     ImagePullBackOff   0          30s

kubectl describe pod -l app=scenario-09-bad-image
# Events:
#   Warning  Failed   Failed to pull image "this-registry-does-not-exist.example.com/...":
#            rpc error: ... name unknown: ...
```

### Variant B – Missing imagePullSecret

```bash
# First substitute your registry placeholder
REGISTRY="us-central1-docker.pkg.dev/my-project/my-repo"
sed "s|REGISTRY_PLACEHOLDER|${REGISTRY}|g" k8s/deployment-missing-secret.yaml \
  | kubectl apply -f -

kubectl describe pod -l app=scenario-09-missing-secret
# Events:
#   Warning  Failed   Failed to pull image "...": unauthorized: authentication required
```

## Fixing the Scenarios

**Variant A:** Correct the image name to a valid, accessible image:
```yaml
image: gcr.io/google-samples/hello-app:1.0  # publicly available
```

**Variant B:** Create the pull secret and reference it:
```bash
kubectl create secret docker-registry my-registry-credentials \
  --docker-server=<REGISTRY_HOST> \
  --docker-username=_json_key \
  --docker-password="$(cat key.json)"
```
Then add to the pod spec:
```yaml
imagePullSecrets:
  - name: my-registry-credentials
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- Pod status `ImagePullBackOff` or `ErrImagePull`
- `kubectl describe pod` events: `Failed to pull image`, `unauthorized`, or `not found`
- Image name contains obvious typos or non-existent registry hostnames
- `imagePullSecrets` field missing from pod spec for a private registry image
- `kubectl get secret` — the expected pull secret does not exist in the namespace
