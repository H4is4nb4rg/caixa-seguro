"""Camada de repositórios: única parte que conversa com o banco (consultas parametrizadas via SQLAlchemy)."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Caixa, Movimentacao, TokenRevogado, Usuario


class UsuarioRepositorio:
    def __init__(self, db: Session):
        self.db = db

    def por_login(self, login: str) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.login == login))

    def por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.db.get(Usuario, usuario_id)

    def adicionar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        return usuario


class CaixaRepositorio:
    def __init__(self, db: Session):
        self.db = db

    def aberto(self) -> Caixa | None:
        return self.db.scalar(select(Caixa).where(Caixa.status == "aberto"))

    def ultimo(self) -> Caixa | None:
        return self.db.scalar(select(Caixa).order_by(Caixa.aberto_em.desc()).limit(1))

    def fechados_com_diferenca(self, limite: int = 5) -> list[Caixa]:
        consulta = (
            select(Caixa)
            .where(Caixa.status == "fechado", Caixa.divergencia != 0)
            .order_by(Caixa.fechado_em.desc())
            .limit(limite)
        )
        return list(self.db.scalars(consulta))

    def adicionar(self, caixa: Caixa) -> Caixa:
        self.db.add(caixa)
        self.db.flush()
        return caixa


class MovimentacaoRepositorio:
    def __init__(self, db: Session):
        self.db = db

    def por_id(self, movimentacao_id: uuid.UUID) -> Movimentacao | None:
        return self.db.get(Movimentacao, movimentacao_id)

    def do_caixa(self, caixa_id: uuid.UUID, limite: int = 50) -> list[Movimentacao]:
        consulta = (
            select(Movimentacao)
            .where(Movimentacao.caixa_id == caixa_id)
            .order_by(Movimentacao.registrado_em.desc())
            .limit(limite)
        )
        return list(self.db.scalars(consulta))

    def ativas_do_caixa(self, caixa_id: uuid.UUID) -> list[Movimentacao]:
        consulta = select(Movimentacao).where(
            Movimentacao.caixa_id == caixa_id, Movimentacao.cancelada.is_(False)
        )
        return list(self.db.scalars(consulta))

    def contar(self, caixa_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Movimentacao).where(Movimentacao.caixa_id == caixa_id)
        ) or 0

    def adicionar(self, movimentacao: Movimentacao) -> Movimentacao:
        self.db.add(movimentacao)
        self.db.flush()
        return movimentacao


class TokenRepositorio:
    def __init__(self, db: Session):
        self.db = db

    def revogado(self, jti: str) -> bool:
        return self.db.get(TokenRevogado, jti) is not None

    def revogar(self, jti: str) -> None:
        if not self.revogado(jti):
            self.db.add(TokenRevogado(jti=jti))
            self.db.flush()
