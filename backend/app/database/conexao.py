"""Engine, sessões e base declarativa do banco de dados."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    """Base compartilhada pelos futuros modelos SQLAlchemy."""


def _database_url():
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Defina a variável no ambiente "
            "ou em backend/.env antes de usar o banco de dados."
        )

    parsed_url = make_url(url)
    # URLs postgres:// e postgresql:// não selecionam Psycopg 3 no SQLAlchemy.
    if parsed_url.drivername in {"postgres", "postgresql"}:
        parsed_url = parsed_url.set(drivername="postgresql+psycopg")
    return parsed_url


def criar_engine() -> Engine:
    """Cria engine PostgreSQL com Psycopg 3 e validação de conexões ociosas."""
    return create_engine(_database_url(), pool_pre_ping=True)


engine: Engine | None = criar_engine() if settings.DATABASE_URL else None

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def obter_sessao() -> Generator[Session, None, None]:
    """Dependência FastAPI que fecha a sessão ao final de cada requisição."""
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL não configurada. Defina a variável no ambiente "
            "ou em backend/.env antes de usar o banco de dados."
        )

    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()
