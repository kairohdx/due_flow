import argparse
from getpass import getpass

from dueflow.application.auth import AuthService, DuplicateUserError
from dueflow.config import get_settings
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.database import Database


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="dueflow")
    commands = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = commands.add_parser(
        "create-admin",
        help="cria o usuário administrativo inicial",
    )
    create_admin_parser.add_argument("--email", required=True)
    create_admin_parser.add_argument("--name", required=True)
    args = parser.parse_args()

    if args.command == "create-admin":
        try:
            create_admin(args.email, args.name)
        except (DuplicateUserError, ValueError) as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
