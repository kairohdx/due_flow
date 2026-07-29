from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from dueflow import __version__
from dueflow.api.errors import register_error_handlers
from dueflow.api.auth_dependencies import get_current_user
from dueflow.api.routes.auth import router as auth_router
from dueflow.api.routes.automation import router as automation_router
from dueflow.api.routes.charges import router as charges_router
from dueflow.api.routes.customers import router as customers_router
from dueflow.api.routes.dashboard import router as dashboard_router
from dueflow.api.routes.health import router as health_router
from dueflow.api.routes.notifications import router as notifications_router
from dueflow.api.routes.processing import router as processing_router
from dueflow.api.routes.webhooks import router as webhooks_router
from dueflow.config import Settings, get_settings
from dueflow.infrastructure.db.database import Database


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(webhooks_router)
    protected = [Depends(get_current_user)]
    app.include_router(customers_router, dependencies=protected)
    app.include_router(charges_router, dependencies=protected)
    app.include_router(processing_router, dependencies=protected)
    app.include_router(notifications_router, dependencies=protected)
    app.include_router(automation_router, dependencies=protected)
    app.include_router(dashboard_router, dependencies=protected)
    if app_settings.frontend_dist_path:
        frontend_path = Path(app_settings.frontend_dist_path)
        if not frontend_path.is_dir():
            raise RuntimeError(
                f"frontend compilado não encontrado: {frontend_path}"
            )
        app.mount(
            "/",
            SPAStaticFiles(directory=frontend_path, html=True),
            name="frontend",
        )
    return app


app = create_app()
