"""
Tests for Scenario 04: Connection Refused to Internal Microservice

Tests both the frontend call_backend() helper and the backend handler directly.
"""

import importlib
import json
import io
import sys
import os
import socket
import pytest
import http.server
import threading

# ── Path setup ──────────────────────────────────────────────────────────────
SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "..")
FRONTEND_APP = os.path.join(SCENARIOS_DIR, "frontend", "app")
BACKEND_APP = os.path.join(SCENARIOS_DIR, "backend", "app")

for path in (FRONTEND_APP, BACKEND_APP):
    if path not in sys.path:
        sys.path.insert(0, path)

import importlib
frontend = importlib.import_module("main")
# We need separate module objects for frontend/backend since they're both named 'main'
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

frontend_mod = load_module("frontend_main", FRONTEND_APP)
backend_mod = load_module("backend_main", BACKEND_APP)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_backend_server(port):
    """Start a real backend HTTP server in a daemon thread."""
    server = http.server.HTTPServer(("127.0.0.1", port), backend_mod.BackendHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ── Backend tests ────────────────────────────────────────────────────────────

class TestBackendHandler:
    def _make_request(self, path):
        """Use call_backend to hit a real backend server."""
        port = _free_port()
        server = _start_backend_server(port)
        try:
            return frontend_mod.call_backend(f"http://127.0.0.1:{port}{path}")
        finally:
            server.shutdown()

    def test_api_data_returns_200(self):
        port = _free_port()
        server = _start_backend_server(port)
        try:
            status, body = frontend_mod.call_backend(f"http://127.0.0.1:{port}")
            # call_backend always hits /api/data
            assert status == 200
            data = json.loads(body)
            assert data["source"] == "backend"
        finally:
            server.shutdown()


# ── Frontend call_backend() tests ────────────────────────────────────────────

class TestCallBackend:
    def test_successful_call(self):
        port = _free_port()
        server = _start_backend_server(port)
        try:
            status, body = frontend_mod.call_backend(f"http://127.0.0.1:{port}")
            assert status == 200
            data = json.loads(body)
            assert data["source"] == "backend"
            assert data["status"] == "healthy"
        finally:
            server.shutdown()

    def test_connection_refused_returns_502(self):
        # Use a port that nothing is listening on
        port = _free_port()  # We deliberately do NOT start a server here
        status, body = frontend_mod.call_backend(f"http://127.0.0.1:{port}")
        assert status == 502
        data = json.loads(body)
        assert "Connection refused" in data["error"] or "refused" in data.get("detail", "").lower()

    def test_wrong_port_returns_502(self):
        """Replicates the scenario: BACKEND_URL points to wrong port."""
        status, body = frontend_mod.call_backend("http://127.0.0.1:19999")
        assert status == 502

    def test_response_body_contains_backend_url_on_error(self):
        bad_url = "http://127.0.0.1:19998"
        status, body = frontend_mod.call_backend(bad_url)
        assert status == 502
        data = json.loads(body)
        assert data.get("backend_url") == bad_url


# ── Frontend handler integration tests ───────────────────────────────────────

class TestFrontendHandler:
    """Test the FrontendHandler using a simulated HTTP environment."""

    def _call_handler(self, path, env_vars=None):
        """
        Invoke FrontendHandler.do_GET() by monkey-patching os.environ and
        using a fake request/response object.
        """
        original_env = os.environ.copy()
        if env_vars:
            os.environ.update(env_vars)

        # Build a minimal fake request
        class FakeRequest:
            def makefile(self, *a, **kw):
                return io.BytesIO(f"GET {path} HTTP/1.1\r\n\r\n".encode())

        output = io.BytesIO()

        class FakeSocket:
            def makefile(self, mode, *a, **kw):
                if "r" in mode:
                    return io.BufferedReader(io.BytesIO(f"GET {path} HTTP/1.1\r\n\r\n".encode()))
                return io.BufferedWriter(output)

            def sendall(self, data):
                output.write(data)

        try:
            handler = frontend_mod.FrontendHandler.__new__(frontend_mod.FrontendHandler)
            handler.path = path
            handler.headers = {}
            responses = []
            statuses = []

            def send_response(code, message=None):
                statuses.append(code)
            def send_header(k, v):
                pass
            def end_headers():
                pass
            def write_body(data):
                responses.append(data)

            handler.send_response = send_response
            handler.send_header = send_header
            handler.end_headers = end_headers

            class FakeWFile:
                def write(self, data):
                    responses.append(data)

            handler.wfile = FakeWFile()
            handler.do_GET()
            return statuses[0] if statuses else None, b"".join(responses)
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_healthz_returns_200(self):
        status, body = self._call_handler("/healthz")
        assert status == 200
        assert body == b"ok"

    def test_ready_returns_200(self):
        status, body = self._call_handler("/ready")
        assert status == 200

    def test_missing_backend_url_returns_500(self):
        # Remove BACKEND_URL from env
        env = {k: v for k, v in os.environ.items() if k != "BACKEND_URL"}
        original = os.environ.copy()
        os.environ.clear()
        os.environ.update(env)
        try:
            status, body = self._call_handler("/api/proxy")
            assert status == 500
            data = json.loads(body.decode())
            assert "BACKEND_URL" in data["error"]
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_bad_backend_url_returns_502(self):
        status, body = self._call_handler(
            "/api/proxy",
            env_vars={"BACKEND_URL": "http://127.0.0.1:19997"}
        )
        assert status == 502
