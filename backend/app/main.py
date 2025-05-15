# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import logging
import time

import logfire
import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.api.api_v1.router import api_router
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# Sentry
if isinstance(settings.SENTRY_DSN, str):
    # cf. https://docs.sentry.io/platforms/python/configuration/options/
    sentry_sdk.init(
        settings.SENTRY_DSN,
        enable_tracing=False,
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
        release=settings.VERSION,
        server_name=settings.SERVER_NAME.lower().strip().replace(" ", "-"),
        debug=settings.DEBUG,
        environment=None if settings.DEBUG else "production",
    )
    logger.info(f"Sentry middleware enabled on server {settings.SERVER_NAME}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    debug=settings.DEBUG,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=None,
)


class Status(BaseModel):
    status: str


# Healthcheck
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Healthcheck for the API",
    include_in_schema=False,
)
def health_check() -> Status:
    return Status(status="healthy")


# Routing
app.include_router(api_router, prefix=settings.API_V1_STR)


# Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGIN.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if isinstance(settings.SENTRY_DSN, str):
    app.add_middleware(SentryAsgiMiddleware)  # type: ignore[arg-type]

# APM & Logs
if isinstance(settings.LOGFIRE_TOKEN, str):
    logfire.configure(
        token=settings.LOGFIRE_TOKEN,
        service_name=settings.PROJECT_NAME.lower().strip().replace(" ", "-"),
        service_version=settings.VERSION,
        environment=settings.SERVER_NAME.lower().strip().replace(" ", "-"),
    )
    logfire.instrument_fastapi(
        app, capture_headers=False, excluded_urls=["/docs", "/health", "/api/v1/openapi.json", "/favicon.ico"]
    )
    # logfire.instrument_requests()
    logfire.instrument_system_metrics()
    logger.info(f"Logfire instrumentation enabled on server {settings.SERVER_NAME}")


# Overrides swagger to include favicon
@app.get("/docs", include_in_schema=False)
def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        title=settings.PROJECT_NAME,
        swagger_favicon_url="https://cdn.worldvectorlogo.com/logos/openai-2.svg",
        # Remove schemas from swagger
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    )


# OpenAPI config
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    # https://fastapi.tiangolo.com/tutorial/metadata/
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.PROJECT_DESCRIPTION,
        routes=app.routes,
        license_info={
            "name": "Apache 2.0",
            "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
        },
        contact={
            "name": "API support",
            "email": settings.SUPPORT_EMAIL,
            "url": "https://github.com/frgfm/fastemplate/issues",
        },
    )
    openapi_schema["info"]["x-logo"] = {"url": "https://cdn.worldvectorlogo.com/logos/openai-2.svg"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]
