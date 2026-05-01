"""FastAPI application for scanning repositories and zip uploads."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.scanner_integration import ScanError, scan_github_repo, scan_zip_archive


app = FastAPI(title="AI Code Risk Auditor API")
FRONTEND_PATH = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


@app.get("/")
def index() -> FileResponse:
    """Serve the simple scanner frontend."""
    if not FRONTEND_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Frontend file is missing.",
        )

    return FileResponse(FRONTEND_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple readiness response."""
    return {"status": "ok"}


@app.post("/scan")
async def scan(
    repo_url: str | None = Form(default=None),
    zip_file: UploadFile | None = File(default=None),
    llm_analysis: bool = Form(default=False),
    llm_top_n: int = Form(default=5),
) -> dict[str, Any]:
    """Scan a GitHub repository URL or uploaded zip archive."""
    validate_scan_request(repo_url, zip_file, llm_top_n)

    try:
        if repo_url:
            return scan_github_repo(
                repo_url=repo_url,
                include_llm_analysis=llm_analysis,
                llm_top_n=llm_top_n,
            )

        if zip_file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either repo_url or zip_file.",
            )

        temp_zip_path = await save_upload_to_temp_file(zip_file)
        try:
            return scan_zip_archive(
                temp_zip_path,
                include_llm_analysis=llm_analysis,
                llm_top_n=llm_top_n,
            )
        finally:
            await zip_file.close()
            remove_temp_file(temp_zip_path)
    except ScanError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def validate_scan_request(
    repo_url: str | None,
    zip_file: UploadFile | None,
    llm_top_n: int,
) -> None:
    """Validate mutually exclusive scan inputs and simple bounds."""
    has_repo_url = bool(repo_url and repo_url.strip())
    has_zip_file = zip_file is not None

    if has_repo_url == has_zip_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one input: repo_url or zip_file.",
        )

    if llm_top_n < 0 or llm_top_n > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="llm_top_n must be between 0 and 20.",
        )

    if zip_file is not None and not (zip_file.filename or "").lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zip_file must be a .zip archive.",
        )


async def save_upload_to_temp_file(upload: UploadFile) -> Path:
    """Persist an upload long enough for zip extraction."""
    with NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        while chunk := await upload.read(1024 * 1024):
            temp_file.write(chunk)

        return Path(temp_file.name)


def remove_temp_file(path: Path) -> None:
    """Remove an uploaded temp file after the scan finishes."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
