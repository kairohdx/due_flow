from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dueflow import __version__
from dueflow.api.errors import register_error_handlers
from dueflow.api.routes.automation import router as automation_router
from dueflow.api.routes.charges import router as charges_router
from dueflow.api.routes.customers import router as customers_router
from dueflow.api.routes.health import router as health_router
from dueflow.api.routes.notifications import router as notifications_router
from dueflow.api.routes.processing import router as processing_router
from dueflow.config import Settings, get_settings
from dueflow.infrastructure.db.database import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    database = Database(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        database.dispose()

    app = FastAPI(
        title="DueFlow API",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.database = database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(customers_router)
    app.include_router(charges_router)
    app.include_router(processing_router)
    app.include_router(notifications_router)
    app.include_router(automation_router)
    return app


app = create_app()
