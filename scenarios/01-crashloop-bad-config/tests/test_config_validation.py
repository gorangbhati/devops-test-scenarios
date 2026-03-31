"""
Unit tests for Scenario 01: CrashLoop due to Bad Config.

These tests verify that validate_config() raises SystemExit(1) for bad
configurations and returns the correct dict for valid ones.
"""

import sys
import os
import importlib
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_and_validate(monkeypatch, env: dict):
    """
    Set environment variables via monkeypatch, reload the module, and call
    validate_config().
    """
    # Clear any pre-existing relevant env vars
    for key in ("DATABASE_URL", "APP_PORT", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    # Import fresh to avoid cached state
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
    import main  # noqa: PLC0415
    importlib.reload(main)
    return main.validate_config()


# ---------------------------------------------------------------------------
# Tests: valid configuration
# ---------------------------------------------------------------------------

class TestValidConfig:
    def test_all_valid_values(self, monkeypatch):
        config = _reload_and_validate(monkeypatch, {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "APP_PORT": "8080",
            "LOG_LEVEL": "INFO",
        })
        assert config["database_url"] == "postgresql://user:pass@localhost:5432/db"
        assert config["app_port"] == 8080
        assert config["log_level"] == "INFO"

    def test_log_level_case_insensitive(self, monkeypatch):
        config = _reload_and_validate(monkeypatch, {
            "DATABASE_URL": "postgresql://u:p@h:5432/d",
            "APP_PORT": "3000",
            "LOG_LEVEL": "debug",
        })
        assert config["log_level"] == "DEBUG"

    def test_port_boundary_values(self, monkeypatch):
        for port in ("1", "65535"):
            config = _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgresql://u:p@h:5432/d",
                "APP_PORT": port,
                "LOG_LEVEL": "WARNING",
            })
            assert config["app_port"] == int(port)


# ---------------------------------------------------------------------------
# Tests: invalid / missing configuration (must exit with code 1)
# ---------------------------------------------------------------------------

class TestInvalidConfig:
    def test_missing_database_url(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "APP_PORT": "8080",
                "LOG_LEVEL": "INFO",
            })
        assert exc_info.value.code == 1

    def test_wrong_database_url_scheme(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
                "APP_PORT": "8080",
                "LOG_LEVEL": "INFO",
            })
        assert exc_info.value.code == 1

    def test_app_port_not_a_number(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgresql://u:p@h:5432/d",
                "APP_PORT": "not-a-number",
                "LOG_LEVEL": "INFO",
            })
        assert exc_info.value.code == 1

    def test_app_port_zero(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgresql://u:p@h:5432/d",
                "APP_PORT": "0",
                "LOG_LEVEL": "INFO",
            })
        assert exc_info.value.code == 1

    def test_app_port_too_large(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgresql://u:p@h:5432/d",
                "APP_PORT": "99999",
                "LOG_LEVEL": "INFO",
            })
        assert exc_info.value.code == 1

    def test_invalid_log_level(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgresql://u:p@h:5432/d",
                "APP_PORT": "8080",
                "LOG_LEVEL": "VERBOSE",
            })
        assert exc_info.value.code == 1

    def test_all_missing(self, monkeypatch):
        """All three variables missing — should still exit 1 (reports all errors)."""
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {})
        assert exc_info.value.code == 1

    def test_bad_config_from_default_configmap(self, monkeypatch):
        """Replicate exactly the bad values shipped in k8s/configmap.yaml."""
        with pytest.raises(SystemExit) as exc_info:
            _reload_and_validate(monkeypatch, {
                "DATABASE_URL": "postgres://user:password@db-host:5432/mydb",
                "APP_PORT": "not-a-number",
                "LOG_LEVEL": "VERBOSE",
            })
        assert exc_info.value.code == 1
