from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database.conexao import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401


config = context.config

if engine is None:
    raise RuntimeError(
        "DATABASE_URL não configurada. Defina a variável no ambiente "
        "ou em backend/.env antes de executar migrações."
    )

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Mantém a URL com Psycopg 3 e escapa '%' para ConfigParser.
config.set_main_option(
    "sqlalchemy.url",
    engine.url.render_as_string(hide_password=False).replace("%", "%%"),
)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Evita que o autogenerate proponha remover tabelas fora dos modelos."""
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
