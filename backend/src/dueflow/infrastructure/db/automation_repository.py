from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from dueflow.domain.automation import AutomationState
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.models import AutomationSettings

SETTINGS_ID = 1


@dataclass(frozen=True, slots=True)
class AutomationTick:
    enqueued_at: datetime
    interval_seconds: int


class AutomationRepository:
    def __init__(
        self,
        database: Database,
        *,
        default_interval_seconds: int,
    ) -> None:
        self.database = database
        self.default_interval_seconds = default_interval_seconds

    def get(self) -> AutomationState:
        with self.database.session() as session:
            row = session.get(AutomationSettings, SETTINGS_ID)
            if row is None:
                row = self._create(session)
            return self._state(row)

    def enable(
        self,
        *,
        now: datetime,
        interval_seconds: int | None = None,
    ) -> AutomationState:
        with self.database.session() as session:
            row = session.get(AutomationSettings, SETTINGS_ID)
            if row is None:
                row = self._create(session)
            row.enabled = True
            row.interval_seconds = (
                interval_seconds
                if interval_seconds is not None
                else row.interval_seconds
            )
            row.next_run_at = now
            row.updated_at = now
            session.commit()
            session.refresh(row)
            return self._state(row)

    def disable(self, *, now: datetime) -> AutomationState:
        with self.database.session() as session:
            row = session.get(AutomationSettings, SETTINGS_ID)
            if row is None:
                row = self._create(session)
            row.enabled = False
            row.next_run_at = None
            row.updated_at = now
            session.commit()
            session.refresh(row)
            return self._state(row)

    def configure(
        self,
        *,
        now: datetime,
        interval_seconds: int,
    ) -> AutomationState:
        with self.database.session() as session:
            row = session.get(AutomationSettings, SETTINGS_ID)
            if row is None:
                row = self._create(session)
            row.interval_seconds = interval_seconds
            if row.enabled:
                row.next_run_at = now + timedelta(seconds=interval_seconds)
            row.updated_at = now
            session.commit()
            session.refresh(row)
            return self._state(row)

    def claim_due(self, *, now: datetime) -> AutomationTick | None:
        with self.database.session() as session:
            row = session.get(AutomationSettings, SETTINGS_ID)
            if row is None:
                row = self._create(session)
            next_run_at = self._aware_utc(row.next_run_at)
            if not row.enabled or (
                next_run_at is not None and next_run_at > now
            ):
                return None

            observed_next_run = row.next_run_at
            conditions = [
                AutomationSettings.id == SETTINGS_ID,
                AutomationSettings.enabled.is_(True),
            ]
            if observed_next_run is None:
                conditions.append(AutomationSettings.next_run_at.is_(None))
            else:
                conditions.append(
                    AutomationSettings.next_run_at == observed_next_run
                )
            statement = (
                update(AutomationSettings)
                .where(*conditions)
                .values(
                    last_enqueued_at=now,
                    next_run_at=now + timedelta(seconds=row.interval_seconds),
                    updated_at=now,
                )
            )
            updated = session.execute(statement).rowcount
            session.commit()
            if updated != 1:
                return None
            return AutomationTick(
                enqueued_at=now,
                interval_seconds=row.interval_seconds,
            )

    def _create(self, session) -> AutomationSettings:
        row = AutomationSettings(
            id=SETTINGS_ID,
            enabled=False,
            interval_seconds=self.default_interval_seconds,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(
                select(AutomationSettings).where(
                    AutomationSettings.id == SETTINGS_ID
                )
            )
            if existing is None:
                raise
            return existing
        session.refresh(row)
        return row

    @staticmethod
    def _state(row: AutomationSettings) -> AutomationState:
        return AutomationState(
            enabled=row.enabled,
            interval_seconds=row.interval_seconds,
            last_enqueued_at=AutomationRepository._aware_utc(
                row.last_enqueued_at
            ),
            next_run_at=AutomationRepository._aware_utc(row.next_run_at),
            updated_at=AutomationRepository._aware_utc(row.updated_at),
        )

    @staticmethod
    def _aware_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
