from datetime import UTC, datetime, timedelta
from uuid import UUID

from dueflow.application.worker import Worker
from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationProvider,
    NotificationSubmissionStatus,
)
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.db.models import NotificationAttempt
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider
from dueflow.application.message_delivery import TemplateConfiguration


def create_failed_attempt(
    client,
    database,
    customer,
    *,
    error_code: int,
) -> tuple[dict, str]:
    charge = client.post(
        "/charges",
        json={
            "customer_id": customer["id"],
            "description": "Cobrança para retentativa",
            "amount": "100.00",
            "due_date": "2026-07-29",
        },
    ).json()
    with database.session() as session:
        attempt = NotificationAttempt(
            charge_id=UUID(charge["id"]),
            notification_type=NotificationType.DUE_TODAY,
            provider=NotificationProvider.FAKE,
            destination=customer["phone"],
            message="Mensagem que será reenviada",
            submission_status=NotificationSubmissionStatus.SIMULATED,
            delivery_status=NotificationDeliveryStatus.FAILED,
            delivery_error_code=error_code,
            delivery_error_title="Simulated failure",
            delivery_error_details="Falha controlada para teste.",
            provider_message_id="wamid.fake.retry-source",
            idempotency_key=f"retry-source:{charge['id']}",
            policy_name="DueTodayPolicy",
            decision_reason="charge_is_due_today",
            processed_at=datetime.now(UTC),
            delivery_event_at=datetime.now(UTC),
            delivery_updated_at=datetime.now(UTC),
        )
        session.add(attempt)
        session.commit()
        return charge, str(attempt.id)


def retry_worker(database) -> Worker:
    return Worker(
        database=database,
        queue=DatabaseJobQueue(database),
        provider=FakeWhatsAppProvider(),
        worker_id="retry-worker",
        timezone="America/Sao_Paulo",
        poll_interval_seconds=0.01,
        lock_ttl=timedelta(minutes=5),
    )


def template_retry_worker(database) -> Worker:
    return Worker(
        database=database,
        queue=DatabaseJobQueue(database),
        provider=FakeWhatsAppProvider(),
        worker_id="template-retry-worker",
        timezone="America/Sao_Paulo",
        poll_interval_seconds=0.01,
        lock_ttl=timedelta(minutes=5),
        template_configuration=TemplateConfiguration(
            mode="retry_only",
            name="dueflow_aviso_cobranca_v1",
            language="pt_BR",
        ),
    )


def test_retry_is_decided_by_first_match_and_preserves_attempt_history(
    client,
    database,
    customer,
) -> None:
    _, attempt_id = create_failed_attempt(
        client,
        database,
        customer,
        error_code=130429,
    )
    current_user = client.get("/auth/me").json()

    assessment = client.get(
        f"/notifications/{attempt_id}/recovery"
    ).json()
    first = client.post(f"/notifications/{attempt_id}/retry")
    duplicate = client.post(f"/notifications/{attempt_id}/retry")

    assert assessment["eligible"] is True
    assert assessment["action"] == "retry"
    assert assessment["policy_name"] == "AllowRetryPolicy"
    assert assessment["trace"]["strategy"] == "first_match"
    assert first.status_code == 202
    assert first.json()["created"] is True
    assert duplicate.status_code == 202
    assert duplicate.json()["created"] is False
    assert duplicate.json()["job_id"] == first.json()["job_id"]

    assert retry_worker(database).run_once() is True

    job = client.get(
        f"/processing/jobs/{first.json()['job_id']}"
    ).json()
    family = client.get(
        f"/notifications/{attempt_id}/attempts"
    ).json()
    source_recovery = client.get(
        f"/notifications/{attempt_id}/recovery"
    ).json()

    assert job["status"] == "completed"
    assert job["type"] == "retry_notification"
    assert job["result"]["retried"] is True
    assert job["result"]["cancelled"] is False
    assert len(family) == 2
    source, retried = family
    assert source["attempt_number"] == 1
    assert retried["attempt_number"] == 2
    assert retried["root_attempt_id"] == source["id"]
    assert retried["retry_of_attempt_id"] == source["id"]
    assert (
        retried["retry_requested_by_user_id"]
        == current_user["id"]
    )
    assert retried["processing_job_id"] == job["id"]
    assert retried["submission_status"] == "simulated"
    assert retried["delivery_status"] == "pending"
    assert retried["trace"]["selected_policy"] == "AllowRetryPolicy"
    assert source_recovery["eligible"] is False
    assert source_recovery["reason"] == "newer_attempt_exists"


def test_retry_is_blocked_when_failure_requires_template(
    client,
    database,
    customer,
) -> None:
    _, attempt_id = create_failed_attempt(
        client,
        database,
        customer,
        error_code=131047,
    )

    assessment = client.get(
        f"/notifications/{attempt_id}/recovery"
    ).json()
    response = client.post(f"/notifications/{attempt_id}/retry")

    assert assessment["eligible"] is False
    assert assessment["action"] == "template"
    assert assessment["policy_name"] == "RequireTemplatePolicy"
    assert response.status_code == 409


def test_template_failure_can_be_reenqueued_with_auditable_template(
    client,
    database,
    customer,
) -> None:
    _, attempt_id = create_failed_attempt(
        client,
        database,
        customer,
        error_code=131047,
    )

    assessment = client.get(
        f"/notifications/{attempt_id}/recovery"
    ).json()
    first = client.post(
        f"/notifications/{attempt_id}/retry-template"
    )
    duplicate = client.post(
        f"/notifications/{attempt_id}/retry-template"
    )

    assert assessment["eligible"] is False
    assert assessment["template_eligible"] is True
    assert first.status_code == 202
    assert duplicate.json()["created"] is False
    assert duplicate.json()["job_id"] == first.json()["job_id"]
    assert template_retry_worker(database).run_once() is True

    family = client.get(
        f"/notifications/{attempt_id}/attempts"
    ).json()
    retried = family[1]
    assert retried["message_format"] == "template"
    assert retried["template_info"] == {
        "name": "dueflow_aviso_cobranca_v1",
        "language": "pt_BR",
        "parameters": [
            customer["name"],
            "Cobrança para retentativa",
            "R$ 100,00",
            "29/07/2026",
        ],
    }
    assert retried["provider_response"]["request"]["type"] == "template"
    assert retried["delivery_status"] == "pending"


def test_retry_job_revalidates_business_state_before_sending(
    client,
    database,
    customer,
) -> None:
    charge, attempt_id = create_failed_attempt(
        client,
        database,
        customer,
        error_code=130429,
    )
    accepted = client.post(
        f"/notifications/{attempt_id}/retry"
    ).json()
    assert client.post(
        f"/charges/{charge['id']}/mark-paid"
    ).status_code == 200

    assert retry_worker(database).run_once() is True

    job = client.get(
        f"/processing/jobs/{accepted['job_id']}"
    ).json()
    family = client.get(
        f"/notifications/{attempt_id}/attempts"
    ).json()
    assert job["status"] == "completed"
    assert job["result"]["retried"] is False
    assert job["result"]["cancelled"] is True
    assert job["result"]["recovery"]["action"] == "block"
    assert job["result"]["recovery"]["reason"] == "charge_is_paid"
    assert len(family) == 1
