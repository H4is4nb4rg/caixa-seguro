"""Entidades do MVP: usuario, caixa e movimentacao (conforme a modelagem da Experiência Prática 2)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

PERFIS = ("proprietaria", "caixa", "vendedora")
TIPOS_MOVIMENTACAO = ("venda", "desconto", "troca", "sangria", "pagamento")
FORMAS_PAGAMENTO = ("dinheiro", "pix", "debito", "credito")


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    login: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=agora)

    __table_args__ = (
        CheckConstraint(f"perfil IN {PERFIS}", name="ck_usuario_perfil"),
    )


class Caixa(Base):
    __tablename__ = "caixa"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="aberto")
    valor_inicial: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    aberto_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=agora)
    usuario_abertura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usuario_fechamento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    valor_esperado: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    valor_contado: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    divergencia: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    justificativa: Mapped[str | None] = mapped_column(String(300))

    usuario_abertura: Mapped[Usuario] = relationship(foreign_keys=[usuario_abertura_id])
    usuario_fechamento: Mapped[Usuario | None] = relationship(foreign_keys=[usuario_fechamento_id])
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        back_populates="caixa", order_by="Movimentacao.registrado_em.desc()"
    )

    __table_args__ = (
        CheckConstraint("status IN ('aberto', 'fechado')", name="ck_caixa_status"),
        CheckConstraint("valor_inicial >= 0", name="ck_caixa_valor_inicial"),
        # Garante, no próprio banco, que só exista um caixa aberto por vez.
        Index(
            "ux_caixa_unico_aberto",
            "status",
            unique=True,
            sqlite_where=text("status = 'aberto'"),
            postgresql_where=text("status = 'aberto'"),
        ),
    )


class Movimentacao(Base):
    __tablename__ = "movimentacao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    caixa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caixa.id"), nullable=False, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    forma_pagamento: Mapped[str | None] = mapped_column(String(10))
    observacao: Mapped[str | None] = mapped_column(String(200))
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora, index=True
    )
    cancelada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motivo_cancelamento: Mapped[str | None] = mapped_column(String(200))
    cancelada_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))

    caixa: Mapped[Caixa] = relationship(back_populates="movimentacoes")
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    cancelada_por: Mapped[Usuario | None] = relationship(foreign_keys=[cancelada_por_id])

    __table_args__ = (
        CheckConstraint(f"tipo IN {TIPOS_MOVIMENTACAO}", name="ck_mov_tipo"),
        CheckConstraint("valor > 0", name="ck_mov_valor"),
    )


class TokenRevogado(Base):
    """Identificadores (jti) de tokens encerrados pelo botão Sair."""

    __tablename__ = "token_revogado"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    revogado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=agora)
