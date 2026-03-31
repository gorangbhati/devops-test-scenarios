"""
Scenario 07: Pods Can't Resolve DNS
=====================================
This Python app performs DNS lookups via socket.getaddrinfo() to demonstrate
what happens when Kubernetes pods cannot resolve hostnames — for example when
CoreDNS is misconfigured or unavailable.

Endpoints:
  GET /dns-check  — resolves UPSTREAM_HOST; returns 200 on success, 503 on failure
  GET /healthz    — liveness probe (always 200)
  GET /ready      — readiness probe (always 200)

Environment variables:
  APP_PORT      — port to listen on (default: 8080)
  UPSTREAM_HOST — hostname to resolve (default: kubernetes.default.svc.cluster.local)
"""

import http.server
import json
import logging
import os
import socket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def resolve_host(hostname: str) -> tuple:
    """
    Attempt DNS resolution for hostname.
    Returns (success: bool, message: str, addresses: list[str]).
    """
    try:
        results = socket.getaddrinfo(hostname, None)
        ips = sorted({r[4][0] for r in results})
        return True, f"Resolved {hostname!r} -> {ips}", ips
    except socket.gaierror as exc:
        msg = f"DNS resolution failed for {hostname!r}: {exc}"
        logging.error(msg)
        return False, msg, []


class DnsCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/dns-check":
            host = os.environ.get("UPSTREAM_HOST", "kubernetes.default.svc.cluster.local")
            success, message, addresses = resolve_host(host)
            status = 200 if success else 503
            self._respond(status, {
                "host": host,
                "resolved": success,
                "addresses": addresses,
                "message": message,
            })

        elif self.path in ("/healthz", "/ready"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

    def _respond(self, status: int, body: dict):
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        logging.debug(fmt, *args)


def main():
    port = int(os.environ.get("APP_PORT", "8080"))
    upstream = os.environ.get("UPSTREAM_HOST", "kubernetes.default.svc.cluster.local")
    logging.info("Scenario 07 app starting on port %d", port)
    logging.info("UPSTREAM_HOST = %s", upstream)
    server = http.server.HTTPServer(("0.0.0.0", port), DnsCheckHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
