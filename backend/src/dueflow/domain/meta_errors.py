from dataclasses import dataclass
from enum import Enum


class MetaErrorAction(str, Enum):
    RETRY = "retry"
    FIX = "fix"
    TEMPLATE = "template"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class MetaErrorDescription:
    title: str
    message: str
    action: str
    action_type: MetaErrorAction
    known: bool = True


_ERRORS: dict[int, MetaErrorDescription] = {
    130429: MetaErrorDescription(
        "Limite de envio atingido",
        "O WhatsApp limitou temporariamente o volume de mensagens desta conta.",
        "Aguarde alguns minutos antes de tentar novamente.",
        MetaErrorAction.RETRY,
    ),
    131026: MetaErrorDescription(
        "Mensagem não entregue",
        "O WhatsApp não conseguiu entregar a mensagem ao destinatário.",
        "Confira o número e tente novamente. Se persistir, peça ao cliente que verifique o WhatsApp.",
        MetaErrorAction.REVIEW,
    ),
    131031: MetaErrorDescription(
        "Conta do WhatsApp indisponível",
        "A conta comercial está temporariamente impedida de enviar mensagens.",
        "Verifique a qualidade e as restrições da conta no Gerenciador do WhatsApp.",
        MetaErrorAction.FIX,
    ),
    131047: MetaErrorDescription(
        "Conversa fora da janela de atendimento",
        "A mensagem não foi entregue porque passaram mais de 24 horas desde a última interação do cliente.",
        "Reenvie usando um template aprovado pela Meta.",
        MetaErrorAction.TEMPLATE,
    ),
    131048: MetaErrorDescription(
        "Limite por excesso de mensagens atingido",
        "A Meta limitou o envio por considerar alto o volume recente de mensagens.",
        "Reduza o ritmo de envio e tente novamente mais tarde.",
        MetaErrorAction.RETRY,
    ),
    131049: MetaErrorDescription(
        "Entrega não permitida para preservar a experiência do usuário",
        "A Meta não entregou esta mensagem para limitar comunicações de marketing ao destinatário.",
        "Não repita o envio imediatamente; revise a estratégia e o tipo de mensagem.",
        MetaErrorAction.REVIEW,
    ),
}

_GENERIC = MetaErrorDescription(
    "Falha informada pelo WhatsApp",
    "O WhatsApp não conseguiu processar ou entregar esta mensagem.",
    "Confira os detalhes técnicos e a configuração antes de tentar novamente.",
    MetaErrorAction.REVIEW,
    known=False,
)


def describe_meta_error(code: int | None) -> MetaErrorDescription:
    if code is None:
        return _GENERIC
    return _ERRORS.get(code, _GENERIC)
