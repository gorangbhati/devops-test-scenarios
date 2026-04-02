# Scenario 17: Checkout Service – Unhandled KeyError on Uppercase Region Code

## Overview

This scenario demonstrates a **subtle Python KeyError that causes HTTP 500 errors for a subset of users**, introduced by a missing case-normalisation step that passed all existing QA tests.

A checkout REST API calculates order totals including regional tax rates. Tax rates are stored in a dictionary keyed by **lowercase** ISO alpha-2 region codes (`"us"`, `"eu"`, etc.). The handler catches `ValueError` and `TypeError` for invalid cart items, but does **not** catch `KeyError`. When the mobile client sends an uppercase region code (`"US"`, `"EU"`, etc.), the `_get_tax_rate()` helper raises a `KeyError` that propagates unhandled — Flask converts it to an HTTP 500 response.

The pod stays alive (this is a user-facing error, not a crash), but every checkout request from the mobile app fails with `500 Internal Server Error`.

## Why QA Missed It

| Test input | Outcome |
|---|---|
| `"region": "us"` | ✅ Works — key exists in TAX_RATES |
| `"region": "eu"` | ✅ Works — key exists in TAX_RATES |
| `"region": "US"` | ❌ Never tested — `KeyError: 'US'` → HTTP 500 |

All QA test cases and curl examples used lowercase region codes as documented in the API spec. A subsequent mobile-app update changed the region field to uppercase (`Locale.getCountry()` returns `"US"` on Android), which only reached production after the QA cycle had completed.

## Directory Structure

```
17-unhandled-exception-checkout/
├── app/
│   ├── main.py          # Flask app with the KeyError bug
│   ├── requirements.txt
│   └── Dockerfile
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   └── service.yaml
└── tests/
    └── test_checkout.py  # Tests that pass — no uppercase region tests
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/checkout` | Calculate order total `{"items":[...],"region":"us"}` |
| `GET` | `/api/products` | List available products |
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/ready` | Readiness probe |

## Reproducing the Scenario

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/scenario-17-checkout

kubectl port-forward svc/scenario-17-checkout 8080:80

# 1. Verify the service is healthy
curl http://localhost:8080/healthz

# 2. Working request (lowercase region — happy path)
curl -s -X POST http://localhost:8080/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"items":[{"product_id":"P001","quantity":2}],"region":"us"}' | jq
# → {"region":"us","tax_rate":0.08,"subtotal":59.98,"tax":4.80,"total":64.78,...}

# 3. Failing request (uppercase region — triggers the bug)
curl -sv -X POST http://localhost:8080/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"items":[{"product_id":"P001","quantity":2}],"region":"US"}'
# → HTTP/1.1 500 INTERNAL SERVER ERROR
```

## Confirming the Error in Logs

```bash
kubectl logs -l scenario=17-unhandled-exception-checkout

# ERROR in app: KeyError: 'US'
# Traceback (most recent call last):
#   File ".../flask/app.py", line ..., in full_dispatch_request
#   File ".../flask/app.py", line ..., in dispatch_request
#   File "/app/main.py", line ..., in checkout
#     tax_rate = _get_tax_rate(region)
#   File "/app/main.py", line ..., in _get_tax_rate
#     return TAX_RATES[region]
# KeyError: 'US'
```

## Root Cause in Code

In `app/main.py`, the tax-rate helper:

```python
TAX_RATES = {
    "us": 0.08,
    "eu": 0.20,
    "uk": 0.20,
    "ca": 0.13,
    "au": 0.10,
}

def _get_tax_rate(region: str) -> float:
    return TAX_RATES[region]   # KeyError if region is "US", "EU", etc.
```

And the handler catches the wrong exception types:

```python
try:
    subtotal, line_items = _build_line_items(items)
except ValueError as exc:          # catches item validation errors
    return jsonify({"error": str(exc)}), 400

tax_rate = _get_tax_rate(region)   # KeyError NOT caught → HTTP 500
```

## Fix

Normalise the region code to lowercase before the dict lookup:

```python
def _get_tax_rate(region: str) -> float:
    normalised = region.lower()
    if normalised not in TAX_RATES:
        raise ValueError(
            f"Unsupported region {region!r}. "
            f"Supported: {', '.join(sorted(TAX_RATES))}"
        )
    return TAX_RATES[normalised]
```

Then catch `ValueError` from `_get_tax_rate` in the handler, or move the call inside the existing `try/except` block.

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:

- Spike in HTTP 500 error rate on `POST /api/checkout` (pod stays alive, liveness probe passes)
- Error logs consistently showing `KeyError: 'US'` (or `'EU'`, `'UK'`, etc.)
- Stack trace always terminates at `_get_tax_rate` → `TAX_RATES[region]`
- Errors correlate with requests originating from the mobile app (after its update)
- Lowercase region requests succeed; uppercase region requests fail — the error is deterministic and reproducible
- `kubectl logs` vs `kubectl describe pod`: pod is healthy (no restarts), but logs are full of tracebacks
