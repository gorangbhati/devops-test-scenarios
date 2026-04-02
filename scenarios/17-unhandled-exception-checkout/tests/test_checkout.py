"""
Tests for Scenario 17: Checkout Service.

These tests exercise the happy paths (lowercase region codes) and expected
error conditions.  They do NOT test uppercase region codes, which is exactly
the input that triggers the unhandled KeyError bug in production.

Adding a test like:
    def test_checkout_uppercase_region(client):
        resp = client.post("/api/checkout", json={
            "items": VALID_ITEMS, "region": "US"
        })
        assert resp.status_code == 400   # would fail — actual response is 500

would have caught the bug before it reached production.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import app  # noqa: E402

VALID_ITEMS = [
    {"product_id": "P001", "quantity": 2},
    {"product_id": "P002", "quantity": 1},
]


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Happy-path tests (all use lowercase region codes — the bug is never hit)
# ─────────────────────────────────────────────────────────────────────────────

def test_checkout_us(client):
    resp = client.post("/api/checkout", json={"items": VALID_ITEMS, "region": "us"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["region"] == "us"
    assert data["tax_rate"] == 0.08
    assert data["subtotal"] == round(29.99 * 2 + 49.99, 2)
    assert data["total"] > data["subtotal"]


def test_checkout_eu(client):
    resp = client.post("/api/checkout", json={"items": VALID_ITEMS, "region": "eu"})
    assert resp.status_code == 200
    assert resp.get_json()["tax_rate"] == 0.20


def test_checkout_uk(client):
    resp = client.post("/api/checkout", json={"items": VALID_ITEMS, "region": "uk"})
    assert resp.status_code == 200
    assert resp.get_json()["tax_rate"] == 0.20


def test_checkout_ca(client):
    resp = client.post("/api/checkout", json={"items": VALID_ITEMS, "region": "ca"})
    assert resp.status_code == 200
    assert resp.get_json()["tax_rate"] == 0.13


def test_checkout_au(client):
    resp = client.post("/api/checkout", json={"items": VALID_ITEMS, "region": "au"})
    assert resp.status_code == 200
    assert resp.get_json()["tax_rate"] == 0.10


def test_checkout_multiple_items(client):
    items = [
        {"product_id": "P001", "quantity": 3},
        {"product_id": "P003", "quantity": 1},
        {"product_id": "P005", "quantity": 2},
    ]
    resp = client.post("/api/checkout", json={"items": items, "region": "us"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Error-path tests
# ─────────────────────────────────────────────────────────────────────────────

def test_checkout_missing_region(client):
    resp = client.post("/api/checkout", json={"items": VALID_ITEMS})
    assert resp.status_code == 400


def test_checkout_empty_items(client):
    resp = client.post("/api/checkout", json={"items": [], "region": "us"})
    assert resp.status_code == 400


def test_checkout_unknown_product(client):
    resp = client.post("/api/checkout", json={
        "items": [{"product_id": "XXXX", "quantity": 1}],
        "region": "us",
    })
    assert resp.status_code == 400


def test_checkout_invalid_quantity(client):
    resp = client.post("/api/checkout", json={
        "items": [{"product_id": "P001", "quantity": -1}],
        "region": "us",
    })
    assert resp.status_code == 400


def test_checkout_non_json_body(client):
    resp = client.post("/api/checkout", data="not json",
                       content_type="text/plain")
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Utility endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_list_products(client):
    resp = client.get("/api/products")
    assert resp.status_code == 200
    products = resp.get_json()
    assert isinstance(products, list)
    assert len(products) == 5
    ids = {p["product_id"] for p in products}
    assert ids == {"P001", "P002", "P003", "P004", "P005"}


def test_health_endpoints(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/healthz").data == b"ok"
