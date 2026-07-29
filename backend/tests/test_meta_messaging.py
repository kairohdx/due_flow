import json

import httpx
import pytest

from dueflow.config import Settings
from dueflow.domain.messaging import NotificationAttemptStatus
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider
from dueflow.infrastructure.messaging.meta import (
    MetaWhatsAppError,
    MetaWhatsAppProvider,
    mask_phone,
    sanitize_provider_data,
)
from dueflow.worker import build_provider

TEST_TOKEN = "-".join(["not", "a", "real", "meta", "token"])


def provider_with(handler) -> MetaWhatsAppProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return MetaWhatsAppProvider(
        token=TEST_TOKEN,
        phone_number_id="123456789",
        graph_api_version="v99.0",
        http_client=client,
    )


def test_meta_provider_sends_expected_request_and_returns_safe_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == (
            "https://graph.facebook.com/v99.0/123456789/messages"
        )
        assert request.headers["Authorization"] == f"Bearer {TEST_TOKEN}"
        assert json.loads(request.content) == {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "5511999990000",
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Mensagem de teste",
            },
        }
        return httpx.Response(
            200,
            json={
                "messaging_product": "whatsapp",
                "contacts": [
                    {
                        "input": "5511999990000",
                        "wa_id": "5511999990000",
                    }
                ],
                "messages": [{"id": "wamid.meta-test"}],
            },
        )

    result = provider_with(handler).send_text(
        "+5511999990000",
        "Mensagem de teste",
        correlation_id="attempt-123",
    )

    assert result.status is NotificationAttemptStatus.SENT
    assert result.provider_message_id == "wamid.meta-test"
    assert result.request_payload["to"] == "55*******0000"
    assert result.response_payload["contacts"][0]["input"] == "55*******0000"
    assert result.response_payload["contacts"][0]["wa_id"] == "55*******0000"
    assert result.response_payload["http_status"] == 200
    assert result.response_payload["correlation_id"] == "attempt-123"
    assert TEST_TOKEN not in repr(result)


def test_meta_provider_translates_and_sanitizes_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": (
                        f"Token inválido: {TEST_TOKEN}; "
                        "destino +5511999990000"
                    ),
                    "type": "OAuthException",
                    "code": 190,
                    "error_data": {"access_token": TEST_TOKEN},
                }
            },
        )

    with pytest.raises(MetaWhatsAppError) as captured:
        provider_with(handler).send_text(
            "+5511999990000",
            "Mensagem",
            correlation_id="attempt-123",
        )

    error = str(captured.value)
    assert "HTTP 400" in error
    assert "código 190" in error
    assert "OAuthException" in error
    assert TEST_TOKEN not in error
    assert "5511999990000" not in error


def test_meta_provider_translates_timeout_without_leaking_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout contendo dado sensível", request=request)

    with pytest.raises(
        MetaWhatsAppError,
        match="timeout ao comunicar com a API da Meta",
    ):
        provider_with(handler).send_text(
            "+5511999990000",
            "Mensagem",
            correlation_id="attempt-123",
        )


def test_meta_provider_rejects_success_without_message_id() -> None:
    provider = provider_with(
        lambda request: httpx.Response(200, json={"messages": []})
    )

    with pytest.raises(MetaWhatsAppError, match="não contém identificador"):
        provider.send_text(
            "+5511999990000",
            "Mensagem",
            correlation_id="attempt-123",
        )


def test_provider_data_sanitization_is_recursive_and_bounded() -> None:
    sanitized = sanitize_provider_data(
        {
            "authorization": f"Bearer {TEST_TOKEN}",
            "nested": {
                "to": "+5511999990000",
                "message": f"{TEST_TOKEN}{'x' * 2000}",
            },
        },
        secrets=(TEST_TOKEN,),
    )

    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["to"] == "55*******0000"
    assert TEST_TOKEN not in sanitized["nested"]["message"]
    assert len(sanitized["nested"]["message"]) == 1000
    assert mask_phone("1234") == "****"


def test_worker_selects_provider_from_environment_settings() -> None:
    fake = build_provider(Settings(message_provider="fake", _env_file=None))
    meta = build_provider(
        Settings(
            message_provider="meta",
            meta_whatsapp_token=TEST_TOKEN,
            meta_whatsapp_phone_number_id="123456789",
            meta_graph_api_version="v99.0",
            _env_file=None,
        )
    )

    assert isinstance(fake, FakeWhatsAppProvider)
    assert isinstance(meta, MetaWhatsAppProvider)
