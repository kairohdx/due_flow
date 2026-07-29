from dataclasses import dataclass
from typing import Literal

from dueflow.application.message_templates import format_brl, format_date
from dueflow.domain.messaging import TemplateMessage
from dueflow.infrastructure.db.models import Charge, Customer


@dataclass(frozen=True, slots=True)
class TemplateConfiguration:
    mode: Literal["retry_only", "always"] = "retry_only"
    name: str = ""
    language: str = "pt_BR"

    @property
    def available(self) -> bool:
        return bool(self.name.strip() and self.language.strip())

    @property
    def use_by_default(self) -> bool:
        return self.available and self.mode == "always"

    def render(
        self,
        *,
        customer: Customer,
        charge: Charge,
    ) -> TemplateMessage:
        if not self.available:
            raise RuntimeError("template da Meta não configurado")
        parameters = (
            customer.name,
            charge.description,
            format_brl(charge.amount),
            format_date(charge.due_date),
        )
        preview = (
            f"Olá, {parameters[0]}.\n\n"
            "Este é um lembrete sobre a cobrança referente a "
            f"{parameters[1]}, no valor de {parameters[2]}, "
            f"com vencimento em {parameters[3]}.\n\n"
            "Se o pagamento já foi realizado, desconsidere esta mensagem."
        )
        return TemplateMessage(
            name=self.name,
            language=self.language,
            parameters=parameters,
            preview=preview,
        )
