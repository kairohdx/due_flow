from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from dueflow.infrastructure.db.models import RefreshSession, User


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def get_user(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_refresh_session(self, session_id: UUID) -> RefreshSession | None:
        return self.session.get(RefreshSession, session_id)

    def add_user(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def add_refresh_session(self, refresh_session: RefreshSession) -> RefreshSession:
        self.session.add(refresh_session)
        self.session.commit()
        self.session.refresh(refresh_session)
        return refresh_session

    def rotate_refresh_session(
        self,
        current: RefreshSession,
        replacement: RefreshSession,
    ) -> RefreshSession:
        self.session.add(replacement)
        self.session.flush()
        current.revoked_at = replacement.created_at
        current.last_used_at = replacement.created_at
        current.replaced_by_id = replacement.id
        self.session.commit()
        self.session.refresh(replacement)
        return replacement

    def revoke_refresh_session(self, refresh_session: RefreshSession) -> None:
        self.session.commit()
