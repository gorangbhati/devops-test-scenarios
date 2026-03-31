"""
Tests for Scenario 07: Pods Can't Resolve DNS.

Verifies resolve_host() and HTTP handler responses.
"""

import importlib.util
import json
import os
import pytest

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")


def _load_app():
    spec = importlib.util.spec_from_file_location("scenario_07_main", _APP_PATH)
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
    handler = mod.DnsCheckHandler.__new__(mod.DnsCheckHandler)
    handler.path = path
    handler.wfile = wfile
    handler.send_response = lambda code, msg=None: statuses.append(code)
    handler.send_header = lambda k, v: headers.__setitem__(k, v)
    handler.end_headers = lambda: None
    return handler, statuses, wfile


class TestResolveHost:
    def test_resolves_localhost(self):
        mod = _load_app()
        success, message, addresses = mod.resolve_host("localhost")
        assert success is True
        assert len(addresses) > 0

    def test_resolves_loopback_address(self):
        mod = _load_app()
        success, _, addresses = mod.resolve_host("127.0.0.1")
        assert success is True
        assert "127.0.0.1" in addresses

    def test_nonexistent_hostname_fails(self):
        mod = _load_app()
        success, message, addresses = mod.resolve_host(
            "this-host-does-not-exist.invalid"
        )
        assert success is False
        assert addresses == []
        assert "DNS resolution failed" in message

    def test_returns_tuple_of_three(self):
        mod = _load_app()
        result = mod.resolve_host("localhost")
        assert len(result) == 3


class TestHttpHandlers:
    def test_healthz_returns_200(self):
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/healthz")
        h.do_GET()
        assert statuses[0] == 200
        assert wfile.body == b"ok"

    def test_ready_returns_200(self):
        mod = _load_app()
        h, statuses, _ = make_handler(mod, "/ready")
        h.do_GET()
        assert statuses[0] == 200

    def test_unknown_path_returns_404(self):
        mod = _load_app()
        h, statuses, _ = make_handler(mod, "/not-a-path")
        h.do_GET()
        assert statuses[0] == 404

    def test_dns_check_success_with_resolvable_host(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_HOST", "localhost")
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/dns-check")
        h.do_GET()
        assert statuses[0] == 200
        body = json.loads(wfile.body.decode())
        assert body["resolved"] is True
        assert body["host"] == "localhost"

    def test_dns_check_failure_with_nonexistent_host(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_HOST", "this-does-not-exist.invalid")
        mod = _load_app()
        h, statuses, wfile = make_handler(mod, "/dns-check")
        h.do_GET()
        assert statuses[0] == 503
        body = json.loads(wfile.body.decode())
        assert body["resolved"] is False
        assert "DNS resolution failed" in body["message"]

    def test_dns_check_response_has_required_fields(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_HOST", "localhost")
        mod = _load_app()
        h, _, wfile = make_handler(mod, "/dns-check")
        h.do_GET()
        body = json.loads(wfile.body.decode())
        for field in ("host", "resolved", "addresses", "message"):
            assert field in body, f"missing field {field!r}"
