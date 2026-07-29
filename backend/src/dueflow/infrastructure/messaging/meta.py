import re
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    NotificationProvider,
    ProviderSubmissionError,
    ProviderResult,
    TemplateMessage,
)


class MetaWhatsAppError(ProviderSubmissionError):
    """Erro seguro para persistência e logs, sem credenciais ou resposta bruta."""


def mask_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{digits[:2]}{'*' * (len(digits) - 6)}{digits[-4:]}"


def sanitize_provider_data(
    value: Any,
    *,
    secrets: Sequence[str] = (),
) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if lowered in {"access_token", "authorization", "token"}:
                sanitized[key] = "[REDACTED]"
            elif lowered in {
                "input",
                "phone_number",
                "wa_id",
                "to",
            } and isinstance(item, str):
                sanitized[key] = mask_phone(item)
            else:
                sanitized[key] = sanitize_provider_data(item, secrets=secrets)
        return sanitized
    if isinstance(value, list):
        return [sanitize_provider_data(item, secrets=secrets) for item in value]
    if isinstance(value, str):
        sanitized = value
        for secret in secrets:
            if secret:
                sanitized = sanitized.replace(secret, "[REDACTED]")
        sanitized = re.sub(
            r"\+?\d[\d\s().-]{7,}\d",
            lambda match: mask_phone(match.group()),
            sanitized,
        )
        return sanitized[:1000]
    return value


class MetaWhatsAppProvider:
    name = NotificationProvider.META

    def __init__(
        self,
        *,
        token: str,
        phone_number_id: str,
        graph_api_version: str,
        base_url: str = "https://graph.facebook.com",
        timeout_seconds: float = 10,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._token = token
        self._phone_number_id = phone_number_id
        self._graph_api_version = graph_api_version
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    def send_text(
        self,
        to: str,
        body: str,
        *,
        correlation_id: str,
    ) -> ProviderResult:
        wa_id = to.removeprefix("+")
        request_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": wa_id,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        return self._submit(
            request_payload,
            correlation_id=correlation_id,
        )

    def send_template(
        self,
        to: str,
        template: TemplateMessage,
        *,
        correlation_id: str,
    ) -> ProviderResult:
        request_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.removeprefix("+"),
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
        return self._submit(
            request_payload,
            correlation_id=correlation_id,
        )

    def _submit(
        self,
        request_payload: dict[str, Any],
        *,
        correlation_id: str,
    ) -> ProviderResult:
        url = (
            f"{self._base_url}/{self._graph_api_version}/"
            f"{self._phone_number_id}/messages"
        )
        try:
            if self._http_client is None:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(
                        url,
                        headers=self._headers(),
                        json=request_payload,
                    )
            else:
                response = self._http_client.post(
                    url,
                    headers=self._headers(),
                    json=request_payload,
                    timeout=self._timeout_seconds,
                )
        except httpx.TimeoutException as exc:
            raise MetaWhatsAppError(
                "timeout ao comunicar com a API da Meta",
                outcome_unknown=True,
            ) from exc
        except httpx.RequestError as exc:
            raise MetaWhatsAppError(
                "falha de comunicação com a API da Meta",
                outcome_unknown=True,
            ) from exc

        payload = self._response_json(response)
        if not response.is_success:
            raise self._response_error(response.status_code, payload)
        message_id = self._message_id(payload)
        safe_response = sanitize_provider_data(
            payload,
            secrets=(self._token,),
        )
        if not isinstance(safe_response, dict):
            safe_response = {}
        safe_response["http_status"] = response.status_code
        safe_response["correlation_id"] = correlation_id
        return ProviderResult(
            submission_status=NotificationSubmissionStatus.SUCCEEDED,
            provider_message_id=message_id,
            request_payload=sanitize_provider_data(
                request_payload,
                secrets=(self._token,),
            ),
            response_payload=safe_response,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _response_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            if response.is_success:
                raise MetaWhatsAppError(
                    "resposta inválida da API da Meta",
                    outcome_unknown=True,
                ) from exc
            return {}

    def _response_error(
        self,
        status_code: int,
        payload: Any,
    ) -> MetaWhatsAppError:
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = error.get("code") if isinstance(error, dict) else None
        error_type = error.get("type") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        safe_message = sanitize_provider_data(
            str(message or "erro não detalhado"),
            secrets=(self._token,),
        )
        details = [f"HTTP {status_code}"]
        if code is not None:
            details.append(f"código {code}")
        if error_type:
            details.append(str(error_type)[:100])
        return MetaWhatsAppError(
            f"API da Meta recusou a mensagem ({', '.join(details)}): "
            f"{safe_message}",
            code=code if isinstance(code, int) else None,
            title=str(error_type)[:255] if error_type else None,
        )

    @staticmethod
    def _message_id(payload: Any) -> str:
        if not isinstance(payload, dict):
            raise MetaWhatsAppError(
                "resposta inválida da API da Meta",
                outcome_unknown=True,
            )
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise MetaWhatsAppError(
                "resposta da API da Meta não contém identificador da mensagem",
                outcome_unknown=True,
            )
        first = messages[0]
        message_id = first.get("id") if isinstance(first, dict) else None
        if not isinstance(message_id, str) or not message_id:
            raise MetaWhatsAppError(
                "resposta da API da Meta não contém identificador da mensagem",
                outcome_unknown=True,
            )
        return message_id[:255]
