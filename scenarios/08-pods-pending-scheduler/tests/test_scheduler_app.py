"""
Tests for Scenario 08: Pods Stuck in Pending – Scheduler Failures.

The interesting part of this scenario is at the Kubernetes scheduling level
(impossible nodeSelector + extreme resource requests), not in the application
code.  These tests simply verify the app's HTTP endpoints are healthy.
"""

import importlib.util
import json
import os

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")


def _load_app():
    spec = importlib.util.spec_from_file_location("scenario_08_main", _APP_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeWFile:
    def __init__(self):
        self._buf = b""

    def write(self, data):
        self._buf += data if isinstance(data, bytes) else data.encode()

    @property
    def body(self) -> bytes:
        return self._buf


def make_handler(mod, path):
    statuses = []
    headers = {}
    wfile = FakeWFile()
    handler = mod.HealthHandler.__new__(mod.HealthHandler)
    handler.path = path
    handler.wfile = wfile
    handler.send_response = lambda code, msg=None: statuses.append(code)
    handler.send_header = lambda k, v: headers.__setitem__(k, v)
    handler.end_headers = lambda: None
    return handler, statuses, wfile


class TestHealthHandlers:
    def test_healthz_returns_200_ok(self):
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/healthz")
        h.do_GET()
        assert statuses[0] == 200
        assert wfile.body == b"ok"

    def test_ready_returns_200_ok(self):
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/ready")
        h.do_GET()
        assert statuses[0] == 200
        assert wfile.body == b"ok"

    def test_info_returns_200_json(self):
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/info")
        h.do_GET()
        assert statuses[0] == 200
        body = json.loads(wfile.body.decode())
        assert body["scenario"] == "08-pods-pending-scheduler"
        assert "description" in body

    def test_unknown_path_returns_404(self):
        mod = _load_app()
        h, statuses, _ = make_handler(mod, "/does-not-exist")
        h.do_GET()
        assert statuses[0] == 404
