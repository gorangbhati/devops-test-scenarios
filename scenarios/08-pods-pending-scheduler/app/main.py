"""
Scenario 08: Pods Stuck in Pending – Scheduler Failures
=========================================================
This is a trivial Python health-check server.  The application itself is
completely healthy.  The problem is entirely at the Kubernetes scheduler
level: the Deployment manifest requests resources and node labels that no
cluster node can satisfy, so the pod stays in Pending indefinitely.

Two impossible scheduling constraints ship with this scenario:
  1. nodeSelector: hardware=gpu-v100-ultra  (label does not exist on any node)
  2. resources.requests: cpu=128, memory=2Ti  (exceeds every real node)

Endpoints:
  GET /healthz — liveness probe (always 200)
  GET /ready   — readiness probe (always 200)
  GET /info    — returns scenario description

Environment variables:
  APP_PORT — port to listen on (default: 8080)
"""

import http.server
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path in ("/healthz", "/ready"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        elif self.path == "/info":
            self._respond(200, {
                "scenario": "08-pods-pending-scheduler",
                "description": (
                    "The pod will never be scheduled because the Deployment requests "
                    "resources and node labels that no cluster node can satisfy. "
                    "See k8s/deployment.yaml for details."
                ),
            })

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
    logging.info("Scenario 08 app starting on port %d", port)
    server = http.server.HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
