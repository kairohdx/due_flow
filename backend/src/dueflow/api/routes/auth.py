from fastapi import APIRouter, HTTPException, Request, Response, status

from dueflow.api.auth_dependencies import CurrentUser
from dueflow.api.schemas.auth import (
    AccessTokenResponse,
    CurrentUserResponse,
    LoginRequest,
)
from dueflow.application.auth import AuthenticationError, AuthService
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.dependencies import get_session
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDependency = Annotated[Session, Depends(get_session)]


def service(request: Request, session: Session) -> AuthService:
    return AuthService(AuthRepository(session), request.app.state.settings)


def set_refresh_cookie(
    response: Response,
    request: Request,
    refresh_token: str,
) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        max_age=settings.auth_refresh_token_expires_days * 86_400,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/auth",
    )


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDependency,
) -> AccessTokenResponse:
    try:
        _, tokens = service(request, session).login(
            email=str(payload.email),
            password=payload.password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    set_refresh_cookie(response, request, tokens.refresh_token)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    request: Request,
    response: Response,
    session: SessionDependency,
) -> AccessTokenResponse:
    settings = request.app.state.settings
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token ausente",
        )
    try:
        _, tokens = service(request, session).refresh(refresh_token)
    except AuthenticationError as exc:
        response.delete_cookie(
            settings.auth_refresh_cookie_name,
            path="/auth",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    set_refresh_cookie(response, request, tokens.refresh_token)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: SessionDependency,
) -> None:
    settings = request.app.state.settings
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    service(request, session).logout(refresh_token)
    response.delete_cookie(
        settings.auth_refresh_cookie_name,
        path="/auth",
    )


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
