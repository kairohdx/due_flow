from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dueflow.domain.charges import ChargeStatus
from dueflow.domain.jobs import JobStatus, JobType
from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    NotificationDeliveryStatus,
    NotificationProvider,
)
from dueflow.domain.meta_errors import describe_meta_error
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.db.base import Base, TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    charges: Mapped[list["Charge"]] = relationship(back_populates="customer")


class Charge(TimestampMixin, Base):
    __tablename__ = "charges"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_charges_amount_positive"),
        CheckConstraint(
            "reminder_days_before >= 0",
            name="ck_charges_reminder_days_non_negative",
        ),
        Index("ix_charges_status_due_date", "status", "due_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        index=True,
    )
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[ChargeStatus] = mapped_column(
        SqlEnum(
            ChargeStatus,
            name="charge_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ChargeStatus.PENDING,
        server_default=ChargeStatus.PENDING.value,
    )
    reminder_days_before: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3",
    )

    customer: Mapped[Customer] = relationship(back_populates="charges")
    notification_attempts: Mapped[list["NotificationAttempt"]] = relationship(
        back_populates="charge"
    )


class NotificationAttempt(Base):
    __tablename__ = "notification_attempts"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_notification_attempts_idempotency_key",
        ),
        Index("ix_notification_attempts_processed_at", "processed_at"),
        Index(
            "ix_notification_attempts_provider_message_id",
            "provider_message_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    charge_id: Mapped[UUID] = mapped_column(
        ForeignKey("charges.id", ondelete="RESTRICT"),
        index=True,
    )
    processing_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="SET NULL"),
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SqlEnum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    provider: Mapped[NotificationProvider] = mapped_column(
        SqlEnum(
            NotificationProvider,
            name="notification_provider",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    destination: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    submission_status: Mapped[NotificationSubmissionStatus] = mapped_column(
        "submission_status",
        SqlEnum(
            NotificationSubmissionStatus,
            name="notification_submission_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=True,
        )
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    submission_error_code: Mapped[int | None] = mapped_column(Integer)
    submission_error_title: Mapped[str | None] = mapped_column(String(255))
    submission_error_details: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    policy_name: Mapped[str] = mapped_column(String(120))
    decision_reason: Mapped[str] = mapped_column(String(255))
    trace: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    delivery_status: Mapped[NotificationDeliveryStatus] = mapped_column(
        SqlEnum(
            NotificationDeliveryStatus,
            name="notification_delivery_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=True,
        ),
        default=NotificationDeliveryStatus.NOT_STARTED,
        server_default=NotificationDeliveryStatus.NOT_STARTED.value,
    )
    root_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("notification_attempts.id", ondelete="RESTRICT"),
        index=True,
    )
    retry_of_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("notification_attempts.id", ondelete="RESTRICT"),
        index=True,
    )
    retry_requested_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
    )
    delivery_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    delivery_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    delivery_error_code: Mapped[int | None] = mapped_column(Integer)
    delivery_error_title: Mapped[str | None] = mapped_column(String(255))
    delivery_error_details: Mapped[str | None] = mapped_column(Text)
    delivery_response: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    charge: Mapped[Charge] = relationship(back_populates="notification_attempts")
    processing_job: Mapped["ProcessingJob | None"] = relationship()
    root_attempt: Mapped["NotificationAttempt | None"] = relationship(
        foreign_keys=[root_attempt_id],
        remote_side=[id],
    )
    retry_of_attempt: Mapped["NotificationAttempt | None"] = relationship(
        foreign_keys=[retry_of_attempt_id],
        remote_side=[id],
    )
    retry_requested_by: Mapped["User | None"] = relationship(
        foreign_keys=[retry_requested_by_user_id],
    )

    @property
    def submission_error_info(self) -> dict[str, Any] | None:
        if (
            self.submission_status
            not in {
                NotificationSubmissionStatus.FAILED,
                NotificationSubmissionStatus.UNKNOWN,
            }
        ):
            return None
        description = describe_meta_error(self.submission_error_code)
        return {
            "code": self.submission_error_code,
            "title": description.title,
            "message": description.message,
            "action": description.action,
            "action_type": description.action_type,
            "known": description.known,
            "technical_title": self.submission_error_title,
            "technical_details": self.submission_error_details,
        }

    @property
    def message_format(self) -> str:
        request = (
            self.provider_response.get("request", {})
            if isinstance(self.provider_response, dict)
            else {}
        )
        if isinstance(request, dict) and request.get("type"):
            return str(request["type"])
        if isinstance(self.trace, dict):
            return str(self.trace.get("message_format", "text"))
        return "text"

    @property
    def template_info(self) -> dict[str, Any] | None:
        if self.message_format != "template":
            return None
        request = (
            self.provider_response.get("request", {})
            if isinstance(self.provider_response, dict)
            else {}
        )
        template = request.get("template") if isinstance(request, dict) else None
        if not isinstance(template, dict):
            traced = (
                self.trace.get("template")
                if isinstance(self.trace, dict)
                else None
            )
            return dict(traced) if isinstance(traced, dict) else None
        language = template.get("language", {})
        components = template.get("components", [])
        parameters: list[str] = []
        if isinstance(components, list):
            for component in components:
                if not isinstance(component, dict):
                    continue
                for parameter in component.get("parameters", []):
                    if isinstance(parameter, dict) and "text" in parameter:
                        parameters.append(str(parameter["text"]))
        return {
            "name": str(template.get("name", "")),
            "language": (
                str(language.get("code", ""))
                if isinstance(language, dict)
                else ""
            ),
            "parameters": parameters,
        }

    @property
    def delivery_error_info(self) -> dict[str, Any] | None:
        if self.delivery_status != NotificationDeliveryStatus.FAILED:
            return None
        description = describe_meta_error(self.delivery_error_code)
        return {
            "code": self.delivery_error_code,
            "title": description.title,
            "message": description.message,
            "action": description.action,
            "action_type": description.action_type,
            "known": description.known,
            "technical_title": self.delivery_error_title,
            "technical_details": self.delivery_error_details,
        }


class ProcessingJob(TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        UniqueConstraint(
            "deduplication_key",
            name="uq_processing_jobs_deduplication_key",
        ),
        Index(
            "ix_processing_jobs_available",
            "status",
            "scheduled_for",
            "created_at",
        ),
        CheckConstraint("attempts >= 0", name="ck_processing_jobs_attempts"),
        CheckConstraint(
            "max_attempts >= 1",
            name="ck_processing_jobs_max_attempts",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type: Mapped[JobType] = mapped_column(
        SqlEnum(
            JobType,
            name="processing_job_type",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=True,
        )
    )
    status: Mapped[JobStatus] = mapped_column(
        SqlEnum(
            JobStatus,
            name="processing_job_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=JobStatus.QUEUED,
        server_default=JobStatus.QUEUED.value,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3",
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    deduplication_key: Mapped[str | None] = mapped_column(String(255))
    retain_deduplication_key: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
    )


class AutomationSettings(Base):
    __tablename__ = "automation_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_automation_settings_singleton"),
        CheckConstraint(
            "interval_seconds >= 1",
            name="ck_automation_settings_interval_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
    )
    interval_seconds: Mapped[int] = mapped_column(
        Integer,
        default=120,
        server_default="120",
    )
    last_enqueued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="RefreshSession.user_id",
    )


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        Index("ix_refresh_sessions_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("refresh_sessions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(
        back_populates="refresh_sessions",
        foreign_keys=[user_id],
    )
