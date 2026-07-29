from uuid import uuid4

from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    NotificationProvider,
    ProviderResult,
    TemplateMessage,
)


class FakeWhatsAppProvider:
    name = NotificationProvider.FAKE

    def send_text(
        self,
        to: str,
        body: str,
        *,
        correlation_id: str,
    ) -> ProviderResult:
        wa_id = to.removeprefix("+")
        message_id = f"wamid.fake.{uuid4().hex}"
        request_payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": body,
            },
        }
        response_payload = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": wa_id, "wa_id": wa_id}],
            "messages": [{"id": message_id}],
            "correlation_id": correlation_id,
            "simulated": True,
        }
        return ProviderResult(
            submission_status=NotificationSubmissionStatus.SIMULATED,
            provider_message_id=message_id,
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def send_template(
        self,
        to: str,
        template: TemplateMessage,
        *,
        correlation_id: str,
    ) -> ProviderResult:
        wa_id = to.removeprefix("+")
        message_id = f"wamid.fake.{uuid4().hex}"
        request_payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "template",
            "template": {
                "name": template.name,
                "language": {"code": template.language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": value}
                            for value in template.parameters
                        ],
                    }
                ],
            },
        }
        return ProviderResult(
            submission_status=NotificationSubmissionStatus.SIMULATED,
            provider_message_id=message_id,
            request_payload=request_payload,
            response_payload={
                "messaging_product": "whatsapp",
                "contacts": [{"input": wa_id, "wa_id": wa_id}],
                "messages": [{"id": message_id}],
                "correlation_id": correlation_id,
                "simulated": True,
                "message_format": "template",
            },
        )
