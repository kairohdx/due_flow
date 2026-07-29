from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dueflow.api.schemas.dashboard import DashboardSummaryResponse
from dueflow.application.dashboard import DashboardService
from dueflow.infrastructure.db.dashboard_repository import DashboardRepository
from dueflow.infrastructure.db.dependencies import get_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    session: SessionDependency,
) -> DashboardSummaryResponse:
    summary = DashboardService(DashboardRepository(session)).summary(
        now=datetime.now(UTC)
    )
    return DashboardSummaryResponse.model_validate(summary)
