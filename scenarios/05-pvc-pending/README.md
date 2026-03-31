# Scenario 05: PVC Stuck in Pending

## Overview

This scenario demonstrates a **PersistentVolumeClaim that can never be bound** because it references a `StorageClass` that does not exist in the cluster. Any pod that mounts this PVC also stays in `Pending` indefinitely.

## What Happens

| Resource | State | Reason |
|----------|-------|--------|
| `scenario-05-data` PVC | `Pending` | StorageClass `non-existent-storage-class` not found |
| `scenario-05-pvc-pending` Pod | `Pending` | Waiting for PVC to be bound |

The application itself (`main.py`) is perfectly healthy — it reads and writes files to a mounted directory. The failure is purely at the Kubernetes storage layer.

## Directory Structure

```
05-pvc-pending/
├── app/
│   ├── main.py       # Python app: writes/reads files from DATA_DIR
│   └── Dockerfile
├── k8s/
│   ├── pvc.yaml          # PVC with bad StorageClass  ← the bug
│   ├── configmap.yaml
│   ├── deployment.yaml   # mounts the PVC at /data
│   └── service.yaml
└── tests/
    └── test_pvc_app.py   # pytest tests
```

## Reproducing the Scenario

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# PVC stays in Pending
kubectl get pvc scenario-05-data
# NAME               STATUS    VOLUME  ...
# scenario-05-data   Pending

# Pod also stays in Pending
kubectl get pods -l scenario=05-pvc-pending
# NAME                              READY   STATUS    RESTARTS   AGE
# scenario-05-pvc-pending-xxx-yyy   0/1     Pending   0          2m

# Inspect PVC events
kubectl describe pvc scenario-05-data
# Events:
#   Type     Reason         Message
#   Warning  ProvisioningFailed  storageclass.storage.k8s.io "non-existent-storage-class" not found
```

## Fixing the Scenario

Update `k8s/pvc.yaml` to use an available StorageClass:

```yaml
spec:
  storageClassName: standard   # GKE default; use "hostpath" on local clusters
```

Then re-apply:
```bash
kubectl delete pvc scenario-05-data
kubectl apply -f k8s/pvc.yaml
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- PVC in `Pending` state for more than 30 seconds
- `kubectl describe pvc` shows `ProvisioningFailed` or `no matching StorageClass` events
- Pod in `Pending` state with event: `persistentvolumeclaim "..." not found` or `unbound immediate PersistentVolumeClaim`
- `kubectl get storageclasses` — the requested class does not appear in the list
