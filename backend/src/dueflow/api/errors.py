from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from dueflow.application.errors import ApplicationError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        _: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

