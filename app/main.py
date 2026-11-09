from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers.analyses import router as analyses_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.catalog import router as catalog_router
from app.routers.cvs import router as cvs_router
from app.routers.profile import router as profile_router

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(cvs_router)
app.include_router(analyses_router)
app.include_router(catalog_router)
app.include_router(admin_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/profile", tags=["frontend"])
def profile_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "profile.html")


@app.get("/explore", tags=["frontend"])
def explore_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "explore.html")


@app.get("/", tags=["frontend"])
def home_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "explore.html")


@app.get("/cv", tags=["frontend"])
def cv_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "cv.html")


@app.get("/analysis", tags=["frontend"])
def analysis_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "analysis.html")


@app.get("/health", tags=["health"])
def health() -> dict[str, bool]:
    return {"ok": True}
