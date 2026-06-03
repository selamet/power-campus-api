"""Application factory: middleware, routers and error handling."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.apps.auth.router import router as auth_router
from app.apps.dashboard.router import router as dashboard_router
from app.apps.invites.router import router as invites_router
from app.apps.students.router import router as students_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Return errors as ``{"message": ...}`` to match the frontend client."""
        message = exc.detail if isinstance(exc.detail, str) else "İstek işlenemedi."
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": message},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "Gönderilen veriler geçersiz.",
                "errors": jsonable_encoder(exc.errors()),
            },
        )

    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(students_router, prefix=settings.api_v1_prefix)
    app.include_router(invites_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, Any]:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
