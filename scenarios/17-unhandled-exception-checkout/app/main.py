"""
Scenario 17: Checkout Service – Unhandled KeyError on Uppercase Region Code
============================================================================
A REST API for calculating order totals with regional tax rates.

The application contains a subtle bug in _get_tax_rate():

    TAX_RATES = {"us": 0.08, "eu": 0.20, ...}   # lowercase keys

    def _get_tax_rate(region):
        return TAX_RATES[region]  # KeyError if region is "US", "EU", etc.

The /api/checkout handler catches ValueError and TypeError for item
validation, but does NOT catch KeyError.  When a mobile client sends an
uppercase region code ("US", "EU", etc.), the KeyError propagates unhandled
through Flask, which returns an HTTP 500 to the caller.

Why QA missed it:
  - All QA test cases and curl examples used lowercase region codes
    ("us", "eu", "uk", "ca", "au") which are present in TAX_RATES.
  - A mobile-app update started sending uppercase codes ("US", "EU", …),
    which only reached production after the QA cycle had completed.
  - The missing .lower() normalisation is easy to overlook in code review
    because the happy-path tests provide 100 % coverage of the function.

Environment variables (via ConfigMap):
  APP_PORT — HTTP listen port (default: 8080)
"""

import os
import logging

from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Tax rates keyed by lowercase ISO alpha-2 region code.
# Supported regions: us, eu, uk, ca, au
TAX_RATES = {
    "us": 0.08,
    "eu": 0.20,
    "uk": 0.20,
    "ca": 0.13,
    "au": 0.10,
}

PRODUCTS = {
    "P001": {"name": "Widget Pro",  "unit_price": 29.99},
    "P002": {"name": "Gadget Plus", "unit_price": 49.99},
    "P003": {"name": "SuperDrive",  "unit_price": 99.99},
    "P004": {"name": "MiniTool",    "unit_price": 14.99},
    "P005": {"name": "UltraKit",    "unit_price": 199.99},
}


def _get_tax_rate(region: str) -> float:
    """Return the tax rate for the given region code.

    Supported regions (lowercase): us, eu, uk, ca, au

    BUG: region is not normalised to lowercase before the dict lookup.
    Mobile clients send uppercase codes ("US", "EU", "UK", etc.) which are
    not present in TAX_RATES.  This raises an uncaught KeyError that Flask
    propagates as HTTP 500 to the caller.

    The try/except block in checkout() catches ValueError and TypeError for
    item validation, but the developer did not account for KeyError from
    this helper — leaving uppercase inputs completely unhandled.
    """
    return TAX_RATES[region]  # KeyError if region is "US", "EU", etc.


def _build_line_items(items: list) -> tuple:
    """Validate cart items and return (subtotal, line_items).

    Raises ValueError for unknown products or invalid quantities.
    """
    line_items = []
    subtotal = 0.0

    for item in items:
        product_id = item.get("product_id", "")
        quantity = item.get("quantity", 1)

        if product_id not in PRODUCTS:
            raise ValueError(f"Unknown product_id: {product_id!r}")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"quantity must be an integer, got {quantity!r}")
        if quantity <= 0:
            raise ValueError(f"quantity must be positive, got {quantity}")

        product = PRODUCTS[product_id]
        line_total = product["unit_price"] * quantity
        line_items.append({
            "product_id": product_id,
            "name":       product["name"],
            "unit_price": product["unit_price"],
            "quantity":   quantity,
            "line_total": round(line_total, 2),
        })
        subtotal += line_total

    return round(subtotal, 2), line_items


@app.route("/api/checkout", methods=["POST"])
def checkout():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "request body must be JSON"}), 400

    items = body.get("items", [])
    region = body.get("region", "")

    if not items:
        return jsonify({"error": "items must be a non-empty list"}), 400
    if not region:
        return jsonify({
            "error": "region is required (supported: us, eu, uk, ca, au)"
        }), 400

    try:
        subtotal, line_items = _build_line_items(items)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # _get_tax_rate raises KeyError for uppercase regions ("US", "EU", …).
    # ValueError and TypeError from _build_line_items are caught above, but
    # the developer forgot that _get_tax_rate can raise a KeyError — it is
    # not caught here, so Flask returns HTTP 500 for those requests.
    tax_rate = _get_tax_rate(region)
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    logger.info(
        "Checkout: region=%s items=%d subtotal=%.2f tax=%.2f total=%.2f",
        region, len(line_items), subtotal, tax, total,
    )

    return jsonify({
        "region":   region,
        "items":    line_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax":      tax,
        "total":    total,
    })


@app.route("/api/products", methods=["GET"])
def list_products():
    return jsonify([
        {"product_id": pid, **info}
        for pid, info in PRODUCTS.items()
    ])


@app.route("/healthz")
@app.route("/ready")
def health():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", "8080"))
    logger.info("Scenario 17 checkout server starting on port %d", port)
    logger.info("  POST /api/checkout  — calculate order total with tax")
    logger.info("  GET  /api/products  — list available products")
    app.run(host="0.0.0.0", port=port)
