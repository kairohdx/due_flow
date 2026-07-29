from typing import Protocol

from dueflow.domain.messaging import NotificationProvider, ProviderResult


class WhatsAppProvider(Protocol):
    name: NotificationProvider

    def send_text(
        self,
        to: str,
        body: str,
        *,
        correlation_id: str,
    ) -> ProviderResult: ...

