"""
Tests for Scenario 05: PVC Stuck in Pending.

Verifies the app's file read/write logic and HTTP handler responses.
The PVC-related failure (pod stuck in Pending) is a Kubernetes-level
behaviour that cannot be unit-tested here.
"""

import importlib.util
import json
import os
import pytest

# ── Load module with unique name to avoid collisions when running all tests ──
_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")


def _load_app(env_overrides=None):
    """Load scenario_05 app module fresh, with optional env overrides already applied."""
    spec = importlib.util.spec_from_file_location("scenario_05_main", _APP_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    handler = mod.AppHandler.__new__(mod.AppHandler)
    handler.path = path
    handler.wfile = wfile
    handler.send_response = lambda code, msg=None: statuses.append(code)
    handler.send_header = lambda k, v: headers.__setitem__(k, v)
    handler.end_headers = lambda: None
    return handler, statuses, wfile


# ── write_entry / read_entries unit tests ─────────────────────────────────────

class TestFileOps:
    def test_write_entry_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        mod.write_entry("hello")
        assert os.path.exists(mod._log_file())

    def test_write_entry_returns_timestamped_string(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        entry = mod.write_entry("test-msg")
        assert "test-msg" in entry
        assert "T" in entry and "Z" in entry

    def test_write_entry_appends(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        mod.write_entry("first")
        mod.write_entry("second")
        entries = mod.read_entries()
        assert len(entries) == 2
        assert any("first" in e for e in entries)
        assert any("second" in e for e in entries)

    def test_read_entries_empty_if_no_file(self, tmp_path, monkeypatch):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setenv("DATA_DIR", str(empty_dir))
        mod = _load_app()
        assert mod.read_entries() == []

    def test_write_creates_data_dir_if_missing(self, tmp_path, monkeypatch):
        new_dir = str(tmp_path / "new" / "sub")
        monkeypatch.setenv("DATA_DIR", new_dir)
        mod = _load_app()
        mod.write_entry("creating dir")
        assert os.path.isdir(new_dir)


# ── HTTP handler tests ─────────────────────────────────────────────────────────

class TestHttpHandlers:
    def test_healthz_returns_200(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/healthz")
        h.do_GET()
        assert statuses[0] == 200
        assert wfile.body == b"ok"

    def test_ready_returns_200(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        h, statuses, _ = make_handler(mod, "/ready")
        h.do_GET()
        assert statuses[0] == 200

    def test_write_endpoint_returns_200(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/write")
        h.do_GET()
        assert statuses[0] == 200
        body = json.loads(wfile.body.decode())
        assert "written" in body

    def test_read_endpoint_returns_entries(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        mod.write_entry("pre-seeded")
        h, statuses, wfile = make_handler(mod, "/read")
        h.do_GET()
        assert statuses[0] == 200
        body = json.loads(wfile.body.decode())
        assert body["count"] == 1
        assert any("pre-seeded" in e for e in body["entries"])

    def test_unknown_path_returns_404(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        mod = _load_app()
        h, statuses, _ = make_handler(mod, "/unknown")
        h.do_GET()
        assert statuses[0] == 404
