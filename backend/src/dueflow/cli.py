import argparse
from getpass import getpass

from dueflow.application.auth import (
    AuthService,
    DuplicateUserError,
    UserNotFoundError,
)
from dueflow.config import get_settings
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.messaging.meta import (
    MetaWhatsAppError,
    MetaWhatsAppProvider,
    mask_phone,
)


def create_admin(email: str, name: str, password: str | None = None) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        resolved_password = password or getpass("Senha: ")
        confirmation = getpass("Confirme a senha: ") if password is None else password
        if resolved_password != confirmation:
            raise ValueError("as senhas não coincidem")
        with database.session() as session:
            user = AuthService(AuthRepository(session), settings).create_user(
                email=email,
                name=name,
                password=resolved_password,
            )
        print(f"Usuário criado: {user.email}")
    finally:
        database.dispose()


def reset_password(email: str, password: str | None = None) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        resolved_password = password or getpass("Nova senha: ")
        confirmation = (
            getpass("Confirme a nova senha: ")
            if password is None
            else password
        )
        if resolved_password != confirmation:
            raise ValueError("as senhas não coincidem")
        with database.session() as session:
            user = AuthService(AuthRepository(session), settings).reset_password(
                email=email,
                password=resolved_password,
            )
        print(f"Senha redefinida e sessões revogadas: {user.email}")
    finally:
        database.dispose()


def test_meta(to: str, message: str) -> None:
    settings = get_settings()
    if settings.message_provider != "meta":
        raise ValueError("defina MESSAGE_PROVIDER=meta para realizar o teste")
    if settings.meta_whatsapp_token is None:
        raise ValueError("META_WHATSAPP_TOKEN não configurado")
    provider = MetaWhatsAppProvider(
        token=settings.meta_whatsapp_token.get_secret_value(),
        phone_number_id=settings.meta_whatsapp_phone_number_id,
        graph_api_version=settings.meta_graph_api_version,
        base_url=settings.meta_graph_api_base_url,
        timeout_seconds=settings.meta_request_timeout_seconds,
    )
    result = provider.send_text(
        to,
        message,
        correlation_id="manual-meta-test",
    )
    print(
        "Mensagem aceita pela Meta: "
        f"id={result.provider_message_id} destino={mask_phone(to)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="dueflow")
    commands = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = commands.add_parser(
        "create-admin",
        help="cria o usuário administrativo inicial",
    )
    create_admin_parser.add_argument("--email", required=True)
    create_admin_parser.add_argument("--name", required=True)
    reset_password_parser = commands.add_parser(
        "reset-password",
        help="redefine a senha e revoga as sessões do usuário",
    )
    reset_password_parser.add_argument("--email", required=True)
    test_meta_parser = commands.add_parser(
        "test-meta",
        help="envia uma mensagem real para um número autorizado",
    )
    test_meta_parser.add_argument("--to", required=True)
    test_meta_parser.add_argument(
        "--message",
        default="Teste de integração do DueFlow.",
    )
    args = parser.parse_args()

    if args.command == "create-admin":
        try:
            create_admin(args.email, args.name)
        except (DuplicateUserError, ValueError) as exc:
            parser.error(str(exc))
    elif args.command == "reset-password":
        try:
            reset_password(args.email)
        except (UserNotFoundError, ValueError) as exc:
            parser.error(str(exc))
    elif args.command == "test-meta":
        try:
            test_meta(args.to, args.message)
        except (MetaWhatsAppError, ValueError) as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
