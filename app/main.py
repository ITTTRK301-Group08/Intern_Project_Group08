import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.routers.analyses import router as analyses_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.careers import router as careers_router
from app.routers.catalog import router as catalog_router
from app.routers.cvs import router as cvs_router
from app.routers.dashboard import router as dashboard_router
from app.routers.interviews import router as interviews_router
from app.routers.learning_plans import router as learning_plans_router
from app.routers.profile import router as profile_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)


def _error_message(detail: object) -> str:
    if isinstance(detail, dict) and isinstance(detail.get("message"), str):
        return detail["message"]
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "Request validation failed"
    return "Request failed"


def _validation_details(exc: RequestValidationError) -> list[dict[str, object]]:
    return [
        {key: error[key] for key in ("loc", "msg", "type") if key in error}
        for error in exc.errors()
    ]


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or get_settings()
    application = FastAPI(title=configured.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=configured.cors_allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = jsonable_encoder(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "message": _error_message(detail),
                "detail": detail,
            },
            headers=exc.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = _validation_details(exc)
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "data": None,
                "message": "Request validation failed",
                "detail": details,
            },
        )

    @application.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled request error at %s",
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "message": "Internal server error",
                "detail": "Internal server error",
            },
        )

    application.include_router(auth_router)
    application.include_router(profile_router)
    application.include_router(cvs_router)
    application.include_router(analyses_router)
    application.include_router(interviews_router)
    application.include_router(catalog_router)
    application.include_router(careers_router)
    application.include_router(learning_plans_router)
    application.include_router(dashboard_router)
    application.include_router(admin_router)

    if STATIC_DIR.exists():
        application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/login", tags=["frontend"])
    def login_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "login.html")

    @application.get("/register", tags=["frontend"])
    def register_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "register.html")

    @application.get("/profile", tags=["frontend"])
    def profile_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "profile.html")

    @application.get("/explore", tags=["frontend"])
    def explore_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "explore.html")

    @application.get("/", tags=["frontend"])
    def home_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "explore.html")

    @application.get("/cv", tags=["frontend"])
    def cv_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "cv.html")

    @application.get("/analysis", tags=["frontend"])
    def analysis_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "analysis.html")

    @application.get("/roadmap", tags=["frontend"])
    def roadmap_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "roadmap.html")

    @application.get("/dashboard", tags=["frontend"])
    def dashboard_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "dashboard.html")

    @application.get("/health", tags=["health"])
    def health() -> dict[str, bool]:
        return {"ok": True}

    return application


app = create_app()
