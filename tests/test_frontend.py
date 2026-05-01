"""Simple verification script for the scanner web frontend."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import FRONTEND_CONFIG_PATH, FRONTEND_PATH, app


def test_frontend_file_exists() -> None:
    """Verify the static frontend is available to the backend."""
    assert FRONTEND_PATH.exists()
    assert FRONTEND_CONFIG_PATH.exists()
    html = FRONTEND_PATH.read_text(encoding="utf-8")
    assert "scan-form" in html
    assert "getApiBaseUrl()" in html
    assert 'fetch(`${getApiBaseUrl()}/scan`' in html


def test_frontend_routes_are_registered() -> None:
    """Verify the frontend and API routes are registered."""
    route_paths = {route.path for route in app.routes}

    assert "/" in route_paths
    assert "/config.js" in route_paths
    assert "/health" in route_paths
    assert "/scan" in route_paths


if __name__ == "__main__":
    test_frontend_file_exists()
    test_frontend_routes_are_registered()
    print("Frontend test passed.")
