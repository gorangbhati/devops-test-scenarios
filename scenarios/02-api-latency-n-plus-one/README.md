# Scenario 02: API Latency – N+1 Database Queries

## Overview

This scenario demonstrates a classic performance anti-pattern: **N+1 database queries**.
A REST API fetches a list of orders and then executes a separate SQL query per order to
load its items — instead of a single JOIN.  The result is high latency that grows linearly
with the number of records.

## What Happens

The Node.js/Express application seeds an in-memory SQLite database with **50 orders × 5
items** on startup and exposes two endpoints:

| Endpoint | Pattern | Queries per Request |
|----------|---------|---------------------|
| `GET /api/orders` | **N+1** (intentionally slow) | 51 (1 + 50) |
| `GET /api/orders/optimized` | Single JOIN (the fix) | 1 |

The `X-Query-Count` response header reveals the exact number of SQL statements executed,
making the difference immediately observable by agents or load-testing tools.

## Directory Structure

```
02-api-latency-n-plus-one/
├── app/
│   ├── src/
│   │   ├── db.js        # SQLite setup and seed logic
│   │   └── server.js    # Express server (both endpoints)
│   ├── Dockerfile
│   └── package.json
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   └── service.yaml
└── tests/
    └── api.test.js      # Jest tests
```

## Reproducing the Scenario

```bash
# Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Port-forward to test locally
kubectl port-forward svc/scenario-02-n-plus-one 8080:80

# Slow endpoint (N+1)
time curl -s http://localhost:8080/api/orders | jq length
# Check query count
curl -si http://localhost:8080/api/orders | grep X-Query-Count
# Expected: X-Query-Count: 51

# Fast endpoint (single JOIN)
time curl -s http://localhost:8080/api/orders/optimized | jq length
curl -si http://localhost:8080/api/orders/optimized | grep X-Query-Count
# Expected: X-Query-Count: 1
```

## Load Testing the Difference

```bash
# Install hey (HTTP load generator)
# Slow endpoint
hey -n 100 -c 10 http://localhost:8080/api/orders

# Optimized endpoint
hey -n 100 -c 10 http://localhost:8080/api/orders/optimized
```

## Root Cause in Code

In `src/server.js`, the N+1 endpoint:

```javascript
// 1 query for all orders
const orders = db.prepare('SELECT * FROM orders').all();

// N queries — one per order
const getItems = db.prepare('SELECT * FROM order_items WHERE order_id = ?');
orders.map(order => {
  const items = getItems.all(order.id);   // <-- executed 50 times
  return { ...order, items };
});
```

## Fix

Replace the N+1 loop with a single JOIN and reshape the results in memory:

```javascript
const rows = db.prepare(`
  SELECT o.*, i.*
  FROM orders o
  LEFT JOIN order_items i ON i.order_id = o.id
`).all();
```

## Agentic Troubleshooting Signals

An autonomous agent should detect and act on:
- High p99/p99.9 latency on `GET /api/orders` compared to baseline
- `X-Query-Count` header value scales with record count
- Database slow-query logs showing many identical repeated queries
- APM traces showing hundreds of DB spans per single HTTP request
