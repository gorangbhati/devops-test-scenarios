/**
 * Tests for Scenario 02: N+1 Database Query API
 *
 * Verifies:
 *  - Both endpoints return correct data shapes
 *  - N+1 endpoint makes ORDER_COUNT+1 queries (revealed via X-Query-Count)
 *  - Optimized endpoint makes exactly 1 query
 *  - Both endpoints return identical order/item data
 *  - Health endpoints return 200
 */

'use strict';

const request = require('supertest');
const app = require('../app/src/server');
const { resetDb } = require('../app/src/db');

afterEach(() => {
  resetDb();
});

describe('Health endpoints', () => {
  test('GET /healthz returns 200 ok', async () => {
    const res = await request(app).get('/healthz');
    expect(res.status).toBe(200);
    expect(res.text).toBe('ok');
  });

  test('GET /ready returns 200 ok', async () => {
    const res = await request(app).get('/ready');
    expect(res.status).toBe(200);
    expect(res.text).toBe('ok');
  });
});

describe('N+1 endpoint GET /api/orders', () => {
  test('returns 200 with an array of orders', async () => {
    const res = await request(app).get('/api/orders');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(50);
  });

  test('each order has an items array with 5 entries', async () => {
    const res = await request(app).get('/api/orders');
    for (const order of res.body) {
      expect(Array.isArray(order.items)).toBe(true);
      expect(order.items.length).toBe(5);
    }
  });

  test('X-Query-Count header equals number_of_orders + 1 (N+1 pattern)', async () => {
    const res = await request(app).get('/api/orders');
    const queryCount = parseInt(res.headers['x-query-count'], 10);
    // 1 query for orders + 50 queries for items = 51
    expect(queryCount).toBe(51);
  });
});

describe('Optimized endpoint GET /api/orders/optimized', () => {
  test('returns 200 with an array of orders', async () => {
    const res = await request(app).get('/api/orders/optimized');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(50);
  });

  test('each order has an items array with 5 entries', async () => {
    const res = await request(app).get('/api/orders/optimized');
    for (const order of res.body) {
      expect(Array.isArray(order.items)).toBe(true);
      expect(order.items.length).toBe(5);
    }
  });

  test('X-Query-Count header equals 1 (single JOIN)', async () => {
    const res = await request(app).get('/api/orders/optimized');
    const queryCount = parseInt(res.headers['x-query-count'], 10);
    expect(queryCount).toBe(1);
  });
});

describe('Data consistency between endpoints', () => {
  test('both endpoints return the same order IDs', async () => {
    const [slow, fast] = await Promise.all([
      request(app).get('/api/orders'),
      request(app).get('/api/orders/optimized'),
    ]);
    const slowIds = slow.body.map((o) => o.id).sort((a, b) => a - b);
    const fastIds = fast.body.map((o) => o.id).sort((a, b) => a - b);
    expect(fastIds).toEqual(slowIds);
  });

  test('both endpoints return same item counts per order', async () => {
    const [slow, fast] = await Promise.all([
      request(app).get('/api/orders'),
      request(app).get('/api/orders/optimized'),
    ]);
    const slowCounts = Object.fromEntries(
      slow.body.map((o) => [o.id, o.items.length])
    );
    const fastCounts = Object.fromEntries(
      fast.body.map((o) => [o.id, o.items.length])
    );
    expect(fastCounts).toEqual(slowCounts);
  });
});
