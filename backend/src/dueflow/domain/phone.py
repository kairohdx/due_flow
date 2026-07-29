import re

_ALLOWED_PHONE_CHARACTERS = re.compile(r"^[+\d\s().-]+$")
_NON_DIGITS = re.compile(r"\D")


def normalize_phone(value: str) -> str:
    phone = value.strip()
    if not phone or not _ALLOWED_PHONE_CHARACTERS.fullmatch(phone):
        raise ValueError("telefone contém caracteres inválidos")
    if not phone.startswith("+"):
        raise ValueError("telefone deve incluir o código do país, começando com +")

    digits = _NON_DIGITS.sub("", phone)
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        raise ValueError("telefone deve estar em um formato E.164 válido")
    return f"+{digits}"

