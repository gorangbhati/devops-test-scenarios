"""
Scenario 05: PVC Stuck in Pending
===================================
Simple Python app that reads and writes to a file on a mounted
PersistentVolume.  When the PersistentVolumeClaim cannot be bound
(because the requested StorageClass does not exist), the pod stays
in Pending indefinitely and this server never starts.

Endpoints:
  GET /write   — appends a timestamped entry to DATA_DIR/log.txt
  GET /read    — returns all entries written so far
  GET /healthz — liveness probe
  GET /ready   — readiness probe

Environment variables:
  APP_PORT  — port to listen on (default: 8080)
  DATA_DIR  — directory backed by the PersistentVolume (default: /data)
"""

import http.server
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATA_DIR = os.environ.get("DATA_DIR", "/data")
LOG_FILE = os.path.join(DATA_DIR, "log.txt")


def _data_dir() -> str:
    """Return the current DATA_DIR (read from env at call time for test isolation)."""
    return os.environ.get("DATA_DIR", "/data")


def _log_file() -> str:
    return os.path.join(_data_dir(), "log.txt")


def write_entry(message: str) -> str:
    """Append a timestamped entry to the log file. Returns the entry string."""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = f"{timestamp} {message}"
    d = _data_dir()
    os.makedirs(d, exist_ok=True)
    with open(_log_file(), "a", encoding="utf-8") as fh:
        fh.write(entry + "\n")
    return entry


def read_entries() -> list:
    """Return all log entries.  Returns empty list if the file doesn't exist."""
    lf = _log_file()
    if not os.path.exists(lf):
        return []
    with open(lf, encoding="utf-8") as fh:
        return [line.rstrip("\n") for line in fh if line.strip()]


class AppHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/write":
            try:
                entry = write_entry("write-request")
                self._respond(200, {"written": entry})
            except OSError as exc:
                self._respond(503, {"error": f"Volume not available: {exc}"})

        elif self.path == "/read":
            try:
                entries = read_entries()
                self._respond(200, {"entries": entries, "count": len(entries)})
            except OSError as exc:
                self._respond(503, {"error": f"Volume not available: {exc}"})

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
    logging.info("Scenario 05 app starting on port %d", port)
    logging.info("DATA_DIR = %s", DATA_DIR)
    server = http.server.HTTPServer(("0.0.0.0", port), AppHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
