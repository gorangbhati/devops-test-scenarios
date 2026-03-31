"""
Scenario 01: CrashLoop due to Bad Config
=========================================
This application intentionally validates its configuration on startup.
If any required environment variable is missing or invalid, it exits
with a non-zero exit code — causing Kubernetes to enter CrashLoopBackOff.

Required environment variables:
  DATABASE_URL  - PostgreSQL connection string (must start with "postgresql://")
  APP_PORT      - HTTP port to listen on (must be an integer between 1 and 65535)
  LOG_LEVEL     - Logging level (must be one of: DEBUG, INFO, WARNING, ERROR)
"""

import os
import sys
import http.server
import logging


def validate_config() -> dict:
    """
    Read and validate all required environment variables.
    Raises SystemExit with a descriptive error message if any value is missing
    or invalid.  This is the intentional crash point for the scenario.
    """
    errors = []

    # --- DATABASE_URL ---
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        errors.append("DATABASE_URL is not set")
    elif not database_url.startswith("postgresql://"):
        errors.append(
            f"DATABASE_URL must start with 'postgresql://', got: '{database_url}'"
        )

    # --- APP_PORT ---
    app_port_raw = os.environ.get("APP_PORT", "")
    if not app_port_raw:
        errors.append("APP_PORT is not set")
    else:
        try:
            app_port = int(app_port_raw)
            if not (1 <= app_port <= 65535):
                raise ValueError("out of range")
        except ValueError:
            errors.append(
                f"APP_PORT must be an integer between 1 and 65535, got: '{app_port_raw}'"
            )
            app_port = None

    # --- LOG_LEVEL ---
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
    log_level = os.environ.get("LOG_LEVEL", "")
    if not log_level:
        errors.append("LOG_LEVEL is not set")
    elif log_level.upper() not in valid_levels:
        errors.append(
            f"LOG_LEVEL must be one of {sorted(valid_levels)}, got: '{log_level}'"
        )

    if errors:
        print("FATAL: Configuration validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    return {
        "database_url": database_url,
        "app_port": int(app_port_raw),
        "log_level": log_level.upper(),
    }


class HealthHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler that exposes /healthz and /ready endpoints."""

    def do_GET(self):  # noqa: N802
        if self.path in ("/healthz", "/ready"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

    def log_message(self, fmt, *args):  # silence default access log
        logging.debug(fmt, *args)


def main():
    print("Starting application — validating configuration …", flush=True)

    config = validate_config()  # exits here if config is bad

    logging.basicConfig(level=config["log_level"])
    logging.info("Configuration is valid.")
    logging.info("DATABASE_URL points to: %s", config["database_url"].split("@")[-1])
    logging.info("Listening on port %d", config["app_port"])

    # Bind to all interfaces so that Kubernetes liveness/readiness probes
    # (which originate from the node, not localhost) can reach the server.
    server = http.server.HTTPServer(("0.0.0.0", config["app_port"]), HealthHandler)
    logging.info("Server started — press Ctrl+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    main()
