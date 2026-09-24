import psycopg
from psycopg import sql

from app.settings import DatabaseBootstrapSettings


def main() -> None:
    settings = DatabaseBootstrapSettings()
    with psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_admin_username,
        password=settings.db_admin_password.get_secret_value(),
        sslmode="verify-full",
        sslrootcert=settings.db_ssl_root_cert,
    ) as connection:
        connection.execute("SELECT 1")
        migration_role_exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (settings.db_migration_username,),
        ).fetchone() is not None
        print(f"Migration role exists: {migration_role_exists}")
        if not migration_role_exists:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(settings.db_migration_username),
                    sql.Literal(settings.db_migration_password.get_secret_value()),
                )
            )
        connection.execute(
            sql.SQL("GRANT CONNECT, CREATE ON DATABASE {} TO {}").format(
                sql.Identifier(settings.db_name),
                sql.Identifier(settings.db_migration_username),
            )
        )
        connection.execute(
            sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(
                sql.Identifier(settings.db_migration_username),
            )
        )
        app_role_exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (settings.db_app_username,),
        ).fetchone() is not None
        print(f"App role exists: {app_role_exists}")
        if not app_role_exists:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(settings.db_app_username),
                    sql.Literal(settings.db_app_password.get_secret_value()),
                )
            )
        connection.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(settings.db_name),
                sql.Identifier(settings.db_app_username),
            )
        )
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                sql.Identifier(settings.db_app_username),
            )
        )
    with psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_migration_username,
        password=settings.db_migration_password.get_secret_value(),
        sslmode="verify-full",
        sslrootcert=settings.db_ssl_root_cert,
    ) as connection:
        connection.execute("SELECT 1")


if __name__ == "__main__":
    main()
