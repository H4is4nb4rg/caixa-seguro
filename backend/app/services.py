"""Camada de serviços: concentra as regras de negócio do caixa."""
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Caixa, Movimentacao, Usuario, agora
from app.repositories import (
    CaixaRepositorio,
    MovimentacaoRepositorio,
    TokenRepositorio,
    UsuarioRepositorio,
)
from app.security import criar_token, verificar_senha

ZERO = Decimal("0.00")

# Perfis autorizados para cada operação (verificados no servidor, nunca apenas na interface).
PODE_ABRIR_FECHAR = {"proprietaria", "caixa"}
PODE_REGISTRAR = {"proprietaria", "caixa", "vendedora"}
PODE_CANCELAR = {"proprietaria", "caixa"}


class ErroNegocio(Exception):
    def __init__(self, mensagem: str, status_code: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_code = status_code


def efeito_no_dinheiro(mov: Movimentacao) -> Decimal:
    """Quanto a movimentação altera o dinheiro físico da gaveta do caixa.

    - venda e troca entram na gaveta quando pagas em dinheiro;
    - sangria sempre retira dinheiro da gaveta;
    - pagamento retira dinheiro quando feito em dinheiro (ou sem forma informada);
    - desconto é apenas registrado para rastreabilidade, sem efeito na gaveta.
    """
    if mov.cancelada:
        return ZERO
    if mov.tipo in ("venda", "troca"):
        return mov.valor if mov.forma_pagamento == "dinheiro" else ZERO
    if mov.tipo == "sangria":
        return -mov.valor
    if mov.tipo == "pagamento":
        return -mov.valor if mov.forma_pagamento in (None, "dinheiro") else ZERO
    return ZERO


def calcular_saldo_esperado(valor_inicial: Decimal, movimentacoes: list[Movimentacao]) -> Decimal:
    total = Decimal(valor_inicial) + sum((efeito_no_dinheiro(m) for m in movimentacoes), ZERO)
    return total.quantize(Decimal("0.01"))


class AutenticacaoServico:
    # Controle de tentativas em memória: suficiente para uma única instância do MVP.
    _falhas: dict[str, list[datetime]] = defaultdict(list)

    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepositorio(db)
        self.tokens = TokenRepositorio(db)

    @classmethod
    def limpar_tentativas(cls) -> None:
        cls._falhas.clear()

    def _bloqueado(self, login: str) -> bool:
        limite = datetime.now(timezone.utc) - timedelta(minutes=settings.login_bloqueio_minutos)
        recentes = [t for t in self._falhas[login] if t > limite]
        self._falhas[login] = recentes
        return len(recentes) >= settings.login_max_tentativas

    def entrar(self, login: str, senha: str) -> tuple[str, Usuario]:
        if self._bloqueado(login):
            raise ErroNegocio("Muitas tentativas. Tente novamente em alguns minutos.", 429)
        usuario = self.usuarios.por_login(login)
        if usuario is None or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
            self._falhas[login].append(datetime.now(timezone.utc))
            # Mensagem genérica: não revela se o login existe.
            raise ErroNegocio("Login ou senha inválidos.", 401)
        self._falhas.pop(login, None)
        token, _ = criar_token(usuario.id, usuario.perfil)
        return token, usuario

    def sair(self, jti: str) -> None:
        self.tokens.revogar(jti)
        self.db.commit()


class CaixaServico:
    def __init__(self, db: Session):
        self.db = db
        self.caixas = CaixaRepositorio(db)
        self.movs = MovimentacaoRepositorio(db)

    @staticmethod
    def _exigir_perfil(usuario: Usuario, perfis: set[str]) -> None:
        if usuario.perfil not in perfis:
            raise ErroNegocio("Seu perfil não tem permissão para esta operação.", 403)

    def caixa_aberto_ou_erro(self) -> Caixa:
        caixa = self.caixas.aberto()
        if caixa is None:
            raise ErroNegocio("Não há caixa aberto. Peça a abertura do caixa.", 409)
        return caixa

    def saldo_esperado(self, caixa: Caixa) -> Decimal:
        return calcular_saldo_esperado(caixa.valor_inicial, self.movs.ativas_do_caixa(caixa.id))

    def resumo(self) -> tuple[Caixa | None, Decimal | None, int]:
        caixa = self.caixas.aberto() or self.caixas.ultimo()
        if caixa is None:
            return None, None, 0
        saldo = self.saldo_esperado(caixa) if caixa.status == "aberto" else caixa.valor_esperado
        return caixa, saldo, self.movs.contar(caixa.id)

    def abrir(self, usuario: Usuario, valor_inicial: Decimal) -> Caixa:
        self._exigir_perfil(usuario, PODE_ABRIR_FECHAR)
        if self.caixas.aberto() is not None:
            raise ErroNegocio("Já existe um caixa aberto.", 409)
        try:
            caixa = self.caixas.adicionar(
                Caixa(status="aberto", valor_inicial=valor_inicial, usuario_abertura_id=usuario.id)
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ErroNegocio("Já existe um caixa aberto.", 409)
        return caixa

    def fechar(self, usuario: Usuario, valor_contado: Decimal, justificativa: str | None) -> Caixa:
        self._exigir_perfil(usuario, PODE_ABRIR_FECHAR)
        caixa = self.caixa_aberto_ou_erro()
        esperado = self.saldo_esperado(caixa)
        divergencia = (Decimal(valor_contado) - esperado).quantize(Decimal("0.01"))
        justificativa = (justificativa or "").strip() or None
        if divergencia != ZERO and not justificativa:
            raise ErroNegocio("Explique a diferença para fechar o caixa.", 422)
        caixa.status = "fechado"
        caixa.fechado_em = agora()
        caixa.usuario_fechamento_id = usuario.id
        caixa.valor_esperado = esperado
        caixa.valor_contado = valor_contado
        caixa.divergencia = divergencia
        caixa.justificativa = justificativa
        self.db.commit()
        return caixa


class MovimentacaoServico:
    def __init__(self, db: Session):
        self.db = db
        self.caixa_servico = CaixaServico(db)
        self.movs = MovimentacaoRepositorio(db)

    def registrar(
        self,
        usuario: Usuario,
        tipo: str,
        valor: Decimal,
        forma_pagamento: str | None,
        observacao: str | None,
        mov_id: uuid.UUID | None = None,
    ) -> tuple[Movimentacao, Decimal]:
        CaixaServico._exigir_perfil(usuario, PODE_REGISTRAR)
        caixa = self.caixa_servico.caixa_aberto_ou_erro()

        # Sincronização offline: o mesmo identificador nunca é gravado duas vezes.
        if mov_id is not None:
            existente = self.movs.por_id(mov_id)
            if existente is not None:
                return existente, self.caixa_servico.saldo_esperado(caixa)

        mov = Movimentacao(
            caixa_id=caixa.id,
            usuario_id=usuario.id,  # responsável SEMPRE definido pelo servidor
            tipo=tipo,
            valor=valor,
            forma_pagamento=forma_pagamento,
            observacao=observacao,
            registrado_em=agora(),  # horário SEMPRE definido pelo servidor
        )
        if mov_id is not None:
            mov.id = mov_id
        self.movs.adicionar(mov)
        self.db.commit()
        return mov, self.caixa_servico.saldo_esperado(caixa)

    def cancelar(self, usuario: Usuario, mov_id: uuid.UUID, motivo: str) -> tuple[Movimentacao, Decimal]:
        CaixaServico._exigir_perfil(usuario, PODE_CANCELAR)
        mov = self.movs.por_id(mov_id)
        if mov is None:
            raise ErroNegocio("Movimentação não encontrada.", 404)
        if mov.caixa.status != "aberto":
            raise ErroNegocio("Não é possível cancelar movimentações de um caixa fechado.", 409)
        if mov.cancelada:
            raise ErroNegocio("Esta movimentação já foi cancelada.", 409)
        mov.cancelada = True
        mov.motivo_cancelamento = motivo.strip()
        mov.cancelada_por_id = usuario.id
        self.db.commit()
        return mov, self.caixa_servico.saldo_esperado(mov.caixa)

    def listar(self, limite: int = 50) -> list[Movimentacao]:
        caixa = self.caixa_servico.caixa_aberto_ou_erro()
        return self.movs.do_caixa(caixa.id, limite)
