import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import UUID

from pydantic import SecretStr

from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationSubmissionStatus,
    NotificationProvider,
)
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.db.models import NotificationAttempt

VERIFY_TOKEN = "-".join(["not", "a", "real", "verify", "token"])
APP_SECRET = "-".join(["not", "a", "real", "app", "secret"])
MESSAGE_ID = "wamid.webhook-test"


def configure_webhook(client) -> None:
    client.app.state.settings.meta_webhook_verify_token = SecretStr(VERIFY_TOKEN)
    client.app.state.settings.meta_app_secret = SecretStr(APP_SECRET)


def signed_body(payload: dict) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = "sha256=" + hmac.new(
        APP_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return body, {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
    }


def create_attempt(client, database, customer) -> dict:
    charge = client.post(
        "/charges",
        json={
            "customer_id": customer["id"],
            "description": "Cobrança do webhook",
            "amount": "100.00",
            "due_date": "2026-07-29",
        },
    ).json()
    with database.session() as session:
        session.add(
            NotificationAttempt(
                charge_id=UUID(charge["id"]),
                notification_type=NotificationType.DUE_TODAY,
                provider=NotificationProvider.META,
                destination="+5516994128480",
                message="Mensagem de teste",
                submission_status=NotificationSubmissionStatus.SUCCEEDED,
                delivery_status=NotificationDeliveryStatus.PENDING,
                provider_message_id=MESSAGE_ID,
                idempotency_key=f"webhook:{charge['id']}",
                policy_name="DueTodayPolicy",
                decision_reason="charge_due_today",
                processed_at=datetime.now(UTC),
            )
        )
        session.commit()
    return charge


def webhook_payload(
    status: str,
    timestamp: int,
    *,
    message_id: str = MESSAGE_ID,
    with_error: bool = False,
) -> dict:
    status_payload = {
        "id": message_id,
        "status": status,
        "timestamp": str(timestamp),
        "recipient_id": "5516994128480",
        "internal_1p_only_data": {"webhook_extra_data": "sensitive"},
    }
    if with_error:
        status_payload["errors"] = [
            {
                "code": 131047,
                "title": "Re-engagement message",
                "message": "Re-engagement message",
                "error_data": {
                    "details": (
                        "Message failed because more than 24 hours passed "
                        "for +5516994128480."
                    )
                },
            }
        ]
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "business-account-id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [status_payload],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def post_webhook(client, payload: dict):
    body, headers = signed_body(payload)
    return client.post("/webhooks/meta", content=body, headers=headers)


def test_webhook_verification_requires_matching_token(
    unauthenticated_client,
) -> None:
    configure_webhook(unauthenticated_client)

    accepted = unauthenticated_client.get(
        "/webhooks/meta",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "challenge-123",
        },
    )
    rejected = unauthenticated_client.get(
        "/webhooks/meta",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "challenge-123",
        },
    )

    assert accepted.status_code == 200
    assert accepted.text == "challenge-123"
    assert rejected.status_code == 403


def test_webhook_rejects_missing_or_invalid_signature(
    unauthenticated_client,
) -> None:
    configure_webhook(unauthenticated_client)
    response = unauthenticated_client.post(
        "/webhooks/meta",
        json=webhook_payload("failed", 1_785_325_506),
    )

    assert response.status_code == 401


def test_failed_delivery_is_sanitized_persisted_and_idempotent(
    client,
    database,
    customer,
) -> None:
    configure_webhook(client)
    charge = create_attempt(client, database, customer)
    payload = webhook_payload("failed", 1_785_325_506, with_error=True)

    first = post_webhook(client, payload)
    duplicate = post_webhook(client, payload)
    attempt = client.get(
        f"/charges/{charge['id']}/notifications"
    ).json()["items"][0]

    assert first.status_code == 200
    assert first.json() == {
        "received": True,
        "events": 1,
        "updated": 1,
        "ignored": 0,
        "unknown": 0,
    }
    assert duplicate.json()["ignored"] == 1
    assert attempt["submission_status"] == "succeeded"
    assert attempt["delivery_status"] == "failed"
    assert attempt["delivery_error_code"] == 131047
    assert attempt["delivery_error_title"] == "Re-engagement message"
    assert "24 hours" in attempt["delivery_error_details"]
    assert attempt["delivery_error_info"] == {
        "code": 131047,
        "title": "Conversa fora da janela de atendimento",
        "message": (
            "A mensagem não foi entregue porque passaram mais de 24 horas "
            "desde a última interação do cliente."
        ),
        "action": "Reenvie usando um template aprovado pela Meta.",
        "action_type": "template",
        "known": True,
        "technical_title": "Re-engagement message",
        "technical_details": attempt["delivery_error_details"],
    }
    persisted = json.dumps(attempt["delivery_response"])
    assert "internal_1p_only_data" not in persisted
    assert "webhook_extra_data" not in persisted
    assert "5516994128480" not in persisted
    summary = client.get("/dashboard/summary").json()
    assert summary["submissions_succeeded_last_24h"] == 1
    assert summary["deliveries_failed_last_24h"] == 1


def test_webhook_ignores_unknown_and_out_of_order_statuses(
    client,
    database,
    customer,
) -> None:
    configure_webhook(client)
    charge = create_attempt(client, database, customer)

    assert post_webhook(
        client,
        webhook_payload("delivered", 200),
    ).json()["updated"] == 1
    assert post_webhook(
        client,
        webhook_payload("sent", 100),
    ).json()["ignored"] == 1
    assert post_webhook(
        client,
        webhook_payload("read", 300),
    ).json()["updated"] == 1
    assert post_webhook(
        client,
        webhook_payload("failed", 400, with_error=True),
    ).json()["ignored"] == 1
    assert post_webhook(
        client,
        webhook_payload("failed", 500, message_id="wamid.unknown"),
    ).json()["unknown"] == 1

    attempt = client.get(
        f"/charges/{charge['id']}/notifications"
    ).json()["items"][0]
    assert attempt["delivery_status"] == "read"
    assert attempt["delivery_error_code"] is None
