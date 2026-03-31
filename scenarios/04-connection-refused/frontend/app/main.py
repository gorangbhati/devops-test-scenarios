"""
Scenario 04: Connection Refused to Internal Microservice — Frontend
====================================================================
This frontend service proxies requests to the backend service via the
BACKEND_URL environment variable.

When BACKEND_URL points to the wrong port/host (as shipped in configmap.yaml),
every call to GET /api/proxy will fail with a connection-refused error and
return HTTP 502.  The backend service itself is healthy.

Required environment variables:
  APP_PORT    — port to listen on (default: 8080)
  BACKEND_URL — URL of the backend service (e.g. http://scenario-04-backend:5000)
"""

import http.client
import http.server
import json
import logging
import os
import urllib.parse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def call_backend(backend_url: str) -> tuple[int, str]:
    """
    Calls GET /api/data on the backend service.
    Returns (http_status, body_text).
    On connection error returns (502, error_message).
    """
    parsed = urllib.parse.urlparse(backend_url)
    host = parsed.hostname
    port = parsed.port or 80

    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/api/data")
        resp = conn.getresponse()
        body = resp.read().decode()
        return resp.status, body
    except ConnectionRefusedError as exc:
        msg = f"Connection refused to backend at {backend_url}: {exc}"
        logging.error(msg)
        return 502, json.dumps({"error": "Connection refused", "backend_url": backend_url, "detail": str(exc)})
    except OSError as exc:
        msg = f"OS error connecting to backend at {backend_url}: {exc}"
        logging.error(msg)
        return 502, json.dumps({"error": str(exc), "backend_url": backend_url})


class FrontendHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        backend_url = os.environ.get("BACKEND_URL", "")

        if self.path == "/api/proxy":
            if not backend_url:
                self._respond(500, json.dumps({"error": "BACKEND_URL is not configured"}))
                return
            status, body = call_backend(backend_url)
            self._respond(status, body, content_type="application/json")

        elif self.path in ("/healthz", "/ready"):
            self._respond(200, "ok", content_type="text/plain")

        else:
            self._respond(404, "not found", content_type="text/plain")

    def _respond(self, status: int, body: str, content_type: str = "application/json"):
        encoded = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        logging.debug("frontend: " + fmt, *args)


def main():
    port = int(os.environ.get("APP_PORT", "8080"))
    backend_url = os.environ.get("BACKEND_URL", "<not set>")
    logging.info("Frontend service starting on port %d", port)
    logging.info("BACKEND_URL = %s", backend_url)
    server = http.server.HTTPServer(("0.0.0.0", port), FrontendHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
