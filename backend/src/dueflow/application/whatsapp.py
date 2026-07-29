from typing import Protocol

from dueflow.domain.messaging import (
    NotificationProvider,
    ProviderResult,
    TemplateMessage,
)


class WhatsAppProvider(Protocol):
    name: NotificationProvider

    def send_text(
        self,
        to: str,
        body: str,
        *,
        correlation_id: str,
    ) -> ProviderResult: ...

    def send_template(
        self,
        to: str,
        template: TemplateMessage,
        *,
        correlation_id: str,
    ) -> ProviderResult: ...
