"""
Scenario 04: Connection Refused to Internal Microservice — Backend
===================================================================
Simple Python HTTP server that acts as the backend service.
It responds to GET /api/data with a JSON payload.

Required environment variables:
  APP_PORT  — port to listen on (default: 5000)
"""

import http.server
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class BackendHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/api/data":
            payload = json.dumps({"source": "backend", "status": "healthy", "message": "Hello from the backend service!"})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode())
        elif self.path in ("/healthz", "/ready"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

    def log_message(self, fmt, *args):
        logging.debug("backend: " + fmt, *args)


def main():
    port = int(os.environ.get("APP_PORT", "5000"))
    logging.info("Backend service starting on port %d", port)
    server = http.server.HTTPServer(("0.0.0.0", port), BackendHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
