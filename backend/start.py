"""Production entry point for hosted FastAPI deployments."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Start Uvicorn using the platform-provided PORT value."""
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
