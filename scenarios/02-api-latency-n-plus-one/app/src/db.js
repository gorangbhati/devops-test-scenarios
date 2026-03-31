/**
 * Scenario 02: API Latency caused by N+1 Database Queries
 * =========================================================
 * Sets up an in-memory SQLite database with:
 *   orders       (id, customer_name, created_at)
 *   order_items  (id, order_id, product_name, quantity, price)
 *
 * Seed data: ORDER_COUNT orders, each with ITEMS_PER_ORDER items.
 */

'use strict';

const Database = require('better-sqlite3');

const ORDER_COUNT = 50;
const ITEMS_PER_ORDER = 5;

let _db = null;

/**
 * Returns a shared in-memory SQLite database instance, creating and seeding
 * it on the first call.
 *
 * @param {string} [filename] - Optional path for a file-based DB (used in tests).
 * @returns {Database}
 */
function getDb(filename) {
  if (_db) return _db;

  _db = new Database(filename || ':memory:');

  _db.exec(`
    CREATE TABLE IF NOT EXISTS orders (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_name TEXT    NOT NULL,
      created_at    TEXT    NOT NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id     INTEGER NOT NULL REFERENCES orders(id),
      product_name TEXT    NOT NULL,
      quantity     INTEGER NOT NULL,
      price        REAL    NOT NULL
    );
  `);

  // Seed only when tables are empty
  const existingOrders = _db.prepare('SELECT COUNT(*) AS n FROM orders').get().n;
  if (existingOrders === 0) {
    const insertOrder = _db.prepare(
      'INSERT INTO orders (customer_name, created_at) VALUES (?, ?)'
    );
    const insertItem = _db.prepare(
      'INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)'
    );

    const products = ['Widget', 'Gadget', 'Doohickey', 'Thingamajig', 'Whatchamacallit'];

    const seedMany = _db.transaction(() => {
      for (let o = 1; o <= ORDER_COUNT; o++) {
        const { lastInsertRowid: orderId } = insertOrder.run(
          `Customer ${o}`,
          new Date().toISOString()
        );
        for (let i = 0; i < ITEMS_PER_ORDER; i++) {
          insertItem.run(orderId, products[i % products.length], i + 1, (i + 1) * 9.99);
        }
      }
    });

    seedMany();
    console.log(`Seeded ${ORDER_COUNT} orders × ${ITEMS_PER_ORDER} items each.`);
  }

  return _db;
}

/**
 * Reset the shared DB singleton (used between tests).
 */
function resetDb() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

module.exports = { getDb, resetDb };
