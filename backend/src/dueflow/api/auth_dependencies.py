from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from dueflow.application.auth import AuthenticationError, AuthService
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.models import User

bearer = HTTPBearer(auto_error=False)
SessionDependency = Annotated[Session, Depends(get_session)]
CredentialsDependency = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer),
]


def get_current_user(
    request: Request,
    session: SessionDependency,
    credentials: CredentialsDependency,
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _unauthorized()
    try:
        return AuthService(
            AuthRepository(session),
            request.app.state.settings,
        ).authenticate_access_token(credentials.credentials)
    except AuthenticationError as exc:
        raise _unauthorized() from exc


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUser = Annotated[User, Depends(get_current_user)]
