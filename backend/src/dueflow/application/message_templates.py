from datetime import date
from decimal import Decimal

from dueflow.domain.notifications import NotificationType


def format_brl(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    localized = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {localized}"


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


class MessageRenderer:
    def render(
        self,
        notification_type: NotificationType,
        *,
        customer_name: str,
        charge_description: str,
        amount: Decimal,
        due_date: date,
    ) -> str:
        variables = {
            "name": customer_name,
            "description": charge_description,
            "amount": format_brl(amount),
            "due_date": format_date(due_date),
        }
        templates = {
            NotificationType.UPCOMING: (
                "Olá, {name}! Lembrete: a cobrança \"{description}\", "
                "no valor de {amount}, vence em {due_date}."
            ),
            NotificationType.DUE_TODAY: (
                "Olá, {name}! A cobrança \"{description}\", no valor de "
                "{amount}, vence hoje ({due_date})."
            ),
            NotificationType.OVERDUE: (
                "Olá, {name}! A cobrança \"{description}\", no valor de "
                "{amount}, venceu em {due_date} e continua pendente."
            ),
        }
        return templates[notification_type].format(**variables)

