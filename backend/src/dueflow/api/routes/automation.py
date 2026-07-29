from fastapi import APIRouter, Request

from dueflow.api.schemas.automation import (
    AutomationEnableRequest,
    AutomationConfigureRequest,
    AutomationResponse,
)
from dueflow.application.automation import AutomationService
from dueflow.infrastructure.db.automation_repository import (
    AutomationRepository,
)

router = APIRouter(prefix="/automation", tags=["automation"])


def service(request: Request) -> AutomationService:
    settings = request.app.state.settings
    return AutomationService(
        AutomationRepository(
            request.app.state.database,
            default_interval_seconds=settings.automation_interval_seconds,
        )
    )


@router.get("", response_model=AutomationResponse)
def get_automation(request: Request) -> AutomationResponse:
    return AutomationResponse.model_validate(
        service(request).get(),
        from_attributes=True,
    )


@router.post("/enable", response_model=AutomationResponse)
def enable_automation(
    payload: AutomationEnableRequest,
    request: Request,
) -> AutomationResponse:
    interval = (
        payload.interval_seconds
        if payload.interval_seconds is not None
        else request.app.state.settings.automation_interval_seconds
    )
    return AutomationResponse.model_validate(
        service(request).enable(interval_seconds=interval),
        from_attributes=True,
    )


@router.post("/disable", response_model=AutomationResponse)
def disable_automation(request: Request) -> AutomationResponse:
    return AutomationResponse.model_validate(
        service(request).disable(),
        from_attributes=True,
    )


@router.put("", response_model=AutomationResponse)
def configure_automation(
    payload: AutomationConfigureRequest,
    request: Request,
) -> AutomationResponse:
    return AutomationResponse.model_validate(
        service(request).configure(interval_seconds=payload.interval_seconds),
        from_attributes=True,
    )
