from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import SecretStr
from psycopg import sql

from app.bootstrap_db import main


def bootstrap_settings() -> SimpleNamespace:
    return SimpleNamespace(
        db_host="localhost",
        db_port=5432,
        db_name="gym_management",
        db_admin_username="db_admin",
        db_admin_password=SecretStr("admin-password"),
        db_migration_username="gym_migrator",
        db_migration_password=SecretStr("migration-password"),
        db_app_username="gym_app",
        db_app_password=SecretStr("app-password"),
        db_ssl_root_cert="/tmp/ca.pem",
    )


def test_existing_roles_are_not_recreated_or_reset() -> None:
    admin_connection = MagicMock()
    admin_connection.__enter__.return_value = admin_connection
    admin_connection.execute.return_value.fetchone.return_value = (1,)
    migration_connection = MagicMock()
    migration_connection.__enter__.return_value = migration_connection

    with (
        patch("app.bootstrap_db.DatabaseBootstrapSettings", return_value=bootstrap_settings()),
        patch(
            "app.bootstrap_db.psycopg.connect",
            side_effect=[admin_connection, migration_connection],
        ),
    ):
        main()

    statements = [
        query.as_string() if isinstance(query, sql.Composable) else query
        for query in (call.args[0] for call in admin_connection.execute.call_args_list)
    ]
    assert not any(statement.startswith(("CREATE ROLE", "ALTER ROLE")) for statement in statements)
    assert migration_connection.execute.call_args.args == ("SELECT 1",)


def test_missing_roles_are_created() -> None:
    admin_connection = MagicMock()
    admin_connection.__enter__.return_value = admin_connection
    admin_connection.execute.return_value.fetchone.return_value = None
    migration_connection = MagicMock()
    migration_connection.__enter__.return_value = migration_connection

    with (
        patch("app.bootstrap_db.DatabaseBootstrapSettings", return_value=bootstrap_settings()),
        patch(
            "app.bootstrap_db.psycopg.connect",
            side_effect=[admin_connection, migration_connection],
        ),
    ):
        main()

    statements = [
        query.as_string() if isinstance(query, sql.Composable) else query
        for query in (call.args[0] for call in admin_connection.execute.call_args_list)
    ]
    assert sum(statement.startswith("CREATE ROLE") for statement in statements) == 2
    assert not any(statement.startswith("ALTER ROLE") for statement in statements)
