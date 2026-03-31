/**
 * Scenario 02: API Latency caused by N+1 Database Queries
 * =========================================================
 *
 * Two endpoints expose the same data with very different query patterns:
 *
 *   GET /api/orders           — N+1 pattern: one query for orders, then one
 *                               per order to fetch its items (intentionally slow).
 *
 *   GET /api/orders/optimized — single JOIN query (the correct approach).
 *
 * The response header X-Query-Count reveals how many SQL statements were
 * executed so that agents (and tests) can measure the difference.
 */

'use strict';

const express = require('express');
const rateLimit = require('express-rate-limit');
const { getDb } = require('./db');

const app = express();

// Rate limiter applied to all API endpoints.
// The generous limit (300 req/min) is intentional: this is a test application
// designed to be load-tested to observe N+1 latency, so the limit only guards
// against accidental runaway clients rather than restricting normal test traffic.
const apiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' },
});

// ─────────────────────────────────────────────────────────────────────────────
// Health / readiness endpoints
// ─────────────────────────────────────────────────────────────────────────────

app.get('/healthz', (_req, res) => res.send('ok'));
app.get('/ready', (_req, res) => res.send('ok'));

// ─────────────────────────────────────────────────────────────────────────────
// N+1 endpoint  (the bad pattern)
// ─────────────────────────────────────────────────────────────────────────────

app.get('/api/orders', apiLimiter, (req, res) => {
  const db = getDb();
  let queryCount = 0;

  // Query 1 — fetch all orders
  const orders = db.prepare('SELECT * FROM orders').all();
  queryCount += 1;

  // Queries 2..N+1 — fetch items for each order individually
  const getItems = db.prepare('SELECT * FROM order_items WHERE order_id = ?');
  const result = orders.map((order) => {
    const items = getItems.all(order.id);
    queryCount += 1;
    return { ...order, items };
  });

  res.set('X-Query-Count', String(queryCount));
  res.json(result);
});

// ─────────────────────────────────────────────────────────────────────────────
// Optimized endpoint (single JOIN — the fix)
// ─────────────────────────────────────────────────────────────────────────────

app.get('/api/orders/optimized', apiLimiter, (req, res) => {
  const db = getDb();

  // Single JOIN — all data in one round-trip
  const rows = db.prepare(`
    SELECT
      o.id            AS order_id,
      o.customer_name,
      o.created_at,
      i.id            AS item_id,
      i.product_name,
      i.quantity,
      i.price
    FROM orders o
    LEFT JOIN order_items i ON i.order_id = o.id
    ORDER BY o.id, i.id
  `).all();

  // Reshape flat rows into nested structure
  const ordersMap = new Map();
  for (const row of rows) {
    if (!ordersMap.has(row.order_id)) {
      ordersMap.set(row.order_id, {
        id: row.order_id,
        customer_name: row.customer_name,
        created_at: row.created_at,
        items: [],
      });
    }
    if (row.item_id !== null) {
      ordersMap.get(row.order_id).items.push({
        id: row.item_id,
        product_name: row.product_name,
        quantity: row.quantity,
        price: row.price,
      });
    }
  }

  res.set('X-Query-Count', '1');
  res.json([...ordersMap.values()]);
});

// ─────────────────────────────────────────────────────────────────────────────
// Server start
// ─────────────────────────────────────────────────────────────────────────────

const PORT = parseInt(process.env.APP_PORT || '3000', 10);

// Only auto-start when run directly (not when imported by tests)
if (require.main === module) {
  getDb(); // initialise and seed DB at startup
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Scenario 02 server listening on port ${PORT}`);
    console.log('  GET /api/orders           — N+1 query pattern (slow)');
    console.log('  GET /api/orders/optimized — single JOIN (fast)');
  });
}

module.exports = app;
