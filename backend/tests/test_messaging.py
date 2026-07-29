from datetime import date
from decimal import Decimal

import pytest

from dueflow.application.message_templates import MessageRenderer, format_brl
from dueflow.domain.messaging import NotificationSubmissionStatus
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider


def test_fake_provider_reproduces_meta_text_contract() -> None:
    provider = FakeWhatsAppProvider()

    result = provider.send_text(
        "+5511999990000",
        "Mensagem de teste",
        correlation_id="attempt-123",
    )

    assert (
        result.submission_status
        is NotificationSubmissionStatus.SIMULATED
    )
    assert result.provider_message_id.startswith("wamid.fake.")
    assert result.request_payload == {
        "messaging_product": "whatsapp",
        "to": "5511999990000",
        "type": "text",
        "text": {
            "preview_url": False,
            "body": "Mensagem de teste",
        },
    }
    assert result.response_payload["contacts"] == [
        {
            "input": "5511999990000",
            "wa_id": "5511999990000",
        }
    ]
    assert result.response_payload["messages"] == [
        {"id": result.provider_message_id}
    ]
    assert result.response_payload["correlation_id"] == "attempt-123"
    assert result.response_payload["simulated"] is True


@pytest.mark.parametrize(
    ("notification_type", "expected_fragment"),
    [
        (NotificationType.UPCOMING, "vence em 31/07/2026"),
        (NotificationType.DUE_TODAY, "vence hoje (31/07/2026)"),
        (NotificationType.OVERDUE, "venceu em 31/07/2026"),
    ],
)
def test_templates_render_expected_charge_data(
    notification_type: NotificationType,
    expected_fragment: str,
) -> None:
    message = MessageRenderer().render(
        notification_type,
        customer_name="Maria",
        charge_description="Mensalidade",
        amount=Decimal("1234.50"),
        due_date=date(2026, 7, 31),
    )

    assert message.startswith("Olá, Maria!")
    assert '"Mensalidade"' in message
    assert "R$ 1.234,50" in message
    assert expected_fragment in message


def test_brl_formatter_does_not_lose_decimal_precision() -> None:
    assert format_brl(Decimal("0.10") + Decimal("0.20")) == "R$ 0,30"
