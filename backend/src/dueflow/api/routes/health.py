from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
def health(request: Request) -> HealthResponse:
    try:
        request.app.state.database.check_connection()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="banco de dados indisponível",
        ) from exc
    return HealthResponse(status="ok", database="ok")

