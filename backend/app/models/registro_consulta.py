from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, composite, mapped_column, relationship

from app.database.conexao import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class StatusRegistro(str, enum.Enum):
    TEMPORARIO = "TEMPORARIO"
    PERMANENTE = "PERMANENTE"


@dataclass
class DadosGeograficos:
    mde: Decimal | None = None
    declividade: Decimal | None = None
    tipo_solo: str | None = None
    aptidao_agricola: str | None = None


class RegistroConsulta(Base):
    __tablename__ = "registros_consulta"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_registro_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_registro_longitude"),
        Index("ix_registros_consulta_usuario_data", "usuario_id", "data_consulta"),
        Index("ix_registros_consulta_status_expiracao", "status", "data_expiracao"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    data_consulta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Os nomes físicos preservam o contrato geoespacial consumido pela API.
    _mde: Mapped[Decimal | None] = mapped_column("altitude_m", Numeric(12, 3), nullable=True)
    _declividade: Mapped[Decimal | None] = mapped_column(
        "declividade_percentual", Numeric(9, 3), nullable=True
    )
    _tipo_solo: Mapped[str | None] = mapped_column("tipo_solo", Text, nullable=True)
    _aptidao_agricola: Mapped[str | None] = mapped_column("aptidao_agricola", Text, nullable=True)
    dados_geograficos: Mapped[DadosGeograficos] = composite(
        DadosGeograficos, _mde, _declividade, _tipo_solo, _aptidao_agricola
    )

    status: Mapped[StatusRegistro] = mapped_column(
        Enum(
            StatusRegistro,
            name="status_registro",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=StatusRegistro.TEMPORARIO,
        server_default=StatusRegistro.TEMPORARIO.value,
    )
    data_expiracao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="registros_consulta")

    @property
    def altitude_m(self) -> Decimal | None:
        return self.dados_geograficos.mde

    @property
    def declividade_percentual(self) -> Decimal | None:
        return self.dados_geograficos.declividade

    @property
    def tipo_solo(self) -> str | None:
        return self.dados_geograficos.tipo_solo

    @property
    def aptidao_agricola(self) -> str | None:
        return self.dados_geograficos.aptidao_agricola
