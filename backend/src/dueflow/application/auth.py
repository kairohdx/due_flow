from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import secrets
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import jwt

from dueflow.config import Settings
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.models import RefreshSession, User


class AuthenticationError(Exception):
    pass


class DuplicateUserError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self.password_hasher = PasswordHasher()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().casefold()

    def create_user(
        self,
        *,
        email: str,
        name: str,
        password: str,
        active: bool = True,
    ) -> User:
        normalized_email = self.normalize_email(email)
        normalized_name = name.strip()
        if self.repository.get_user_by_email(normalized_email) is not None:
            raise DuplicateUserError("já existe um usuário com este e-mail")
        if not normalized_name:
            raise ValueError("o nome não pode ser vazio")
        self._validate_password(password)
        user = User(
            email=normalized_email,
            name=normalized_name,
            password_hash=self.password_hasher.hash(password),
            active=active,
        )
        return self.repository.add_user(user)

    def login(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        user = self.repository.get_user_by_email(self.normalize_email(email))
        if user is None or not self._verify_password(user.password_hash, password):
            raise AuthenticationError("e-mail ou senha inválidos")
        if not user.active:
            raise AuthenticationError("usuário inativo")
        return user, self._create_token_pair(user)

    def reset_password(self, *, email: str, password: str) -> User:
        user = self.repository.get_user_by_email(self.normalize_email(email))
        if user is None:
            raise UserNotFoundError("usuário não encontrado")
        self._validate_password(password)
        return self.repository.update_password_and_revoke_sessions(
            user,
            password_hash=self.password_hasher.hash(password),
            revoked_at=datetime.now(timezone.utc),
        )

    def refresh(self, raw_token: str) -> tuple[User, TokenPair]:
        current = self._validate_refresh_token(raw_token)
        user = current.user
        if not user.active:
            raise AuthenticationError("sessão inválida")

        now = datetime.now(timezone.utc)
        secret = secrets.token_urlsafe(32)
        replacement = RefreshSession(
            user_id=user.id,
            token_hash=self._hash_refresh_secret(secret),
            expires_at=now
            + timedelta(days=self.settings.auth_refresh_token_expires_days),
            created_at=now,
        )
        self.repository.rotate_refresh_session(current, replacement)
        return user, TokenPair(
            access_token=self._create_access_token(user, replacement.id, now),
            refresh_token=self._format_refresh_token(replacement.id, secret),
            expires_in=self.settings.jwt_access_token_expires_minutes * 60,
        )

    def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        try:
            refresh_session = self._validate_refresh_token(raw_token)
        except AuthenticationError:
            return
        refresh_session.revoked_at = datetime.now(timezone.utc)
        refresh_session.last_used_at = refresh_session.revoked_at
        self.repository.revoke_refresh_session(refresh_session)

    def authenticate_access_token(self, token: str) -> User:
        try:
            claims = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=["HS256"],
                issuer=self.settings.jwt_issuer,
                audience=self.settings.jwt_audience,
            )
            if claims.get("type") != "access":
                raise AuthenticationError("token de acesso inválido")
            user_id = UUID(str(claims["sub"]))
            session_id = UUID(str(claims["sid"]))
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("token de acesso inválido") from exc

        user = self.repository.get_user(user_id)
        refresh_session = self.repository.get_refresh_session(session_id)
        if (
            user is None
            or not user.active
            or refresh_session is None
            or refresh_session.user_id != user.id
            or refresh_session.revoked_at is not None
            or self._as_utc(refresh_session.expires_at) <= datetime.now(timezone.utc)
        ):
            raise AuthenticationError("token de acesso inválido")
        return user

    def _create_token_pair(self, user: User) -> TokenPair:
        now = datetime.now(timezone.utc)
        secret = secrets.token_urlsafe(32)
        refresh_session = self.repository.add_refresh_session(
            RefreshSession(
                user_id=user.id,
                token_hash=self._hash_refresh_secret(secret),
                expires_at=now
                + timedelta(days=self.settings.auth_refresh_token_expires_days),
                created_at=now,
            )
        )
        return TokenPair(
            access_token=self._create_access_token(user, refresh_session.id, now),
            refresh_token=self._format_refresh_token(refresh_session.id, secret),
            expires_in=self.settings.jwt_access_token_expires_minutes * 60,
        )

    def _create_access_token(
        self,
        user: User,
        session_id: UUID,
        now: datetime,
    ) -> str:
        expires_at = now + timedelta(
            minutes=self.settings.jwt_access_token_expires_minutes
        )
        return jwt.encode(
            {
                "sub": str(user.id),
                "sid": str(session_id),
                "type": "access",
                "iss": self.settings.jwt_issuer,
                "aud": self.settings.jwt_audience,
                "iat": now,
                "nbf": now,
                "exp": expires_at,
            },
            self.settings.jwt_secret,
            algorithm="HS256",
        )

    def _validate_refresh_token(self, raw_token: str) -> RefreshSession:
        try:
            session_id_raw, secret = raw_token.split(".", 1)
            session_id = UUID(session_id_raw)
        except (ValueError, AttributeError) as exc:
            raise AuthenticationError("sessão inválida") from exc

        refresh_session = self.repository.get_refresh_session(session_id)
        now = datetime.now(timezone.utc)
        if (
            refresh_session is None
            or refresh_session.revoked_at is not None
            or self._as_utc(refresh_session.expires_at) <= now
            or not hmac.compare_digest(
                refresh_session.token_hash,
                self._hash_refresh_secret(secret),
            )
        ):
            raise AuthenticationError("sessão inválida")
        return refresh_session

    def _verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self.password_hasher.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 8:
            raise ValueError("a senha deve ter pelo menos 8 caracteres")

    @staticmethod
    def _hash_refresh_secret(secret: str) -> str:
        return sha256(secret.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_refresh_token(session_id: UUID, secret: str) -> str:
        return f"{session_id}.{secret}"

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
