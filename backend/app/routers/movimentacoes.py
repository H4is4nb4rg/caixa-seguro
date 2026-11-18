"""Rotas de movimentações: registrar, listar e cancelar (não existe rota de exclusão)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Movimentacao, Usuario
from app.schemas import CancelamentoEntrada, MovimentacaoEntrada, MovimentacaoSaida, RegistroSaida
from app.services import MovimentacaoServico

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])


def para_saida(mov: Movimentacao) -> MovimentacaoSaida:
    return MovimentacaoSaida(
        id=mov.id,
        caixa_id=mov.caixa_id,
        usuario_id=mov.usuario_id,
        responsavel=mov.usuario.nome,
        tipo=mov.tipo,
        valor=mov.valor,
        forma_pagamento=mov.forma_pagamento,
        observacao=mov.observacao,
        registrado_em=mov.registrado_em,
        cancelada=mov.cancelada,
        motivo_cancelamento=mov.motivo_cancelamento,
        cancelada_por_id=mov.cancelada_por_id,
    )


@router.post("", response_model=RegistroSaida, status_code=201)
def registrar(
    dados: MovimentacaoEntrada, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)
):
    mov, saldo = MovimentacaoServico(db).registrar(
        usuario, dados.tipo, dados.valor, dados.forma_pagamento, dados.observacao, dados.id
    )
    return RegistroSaida(movimentacao=para_saida(mov), saldo_esperado=saldo)


@router.get("", response_model=list[MovimentacaoSaida])
def listar(
    limite: int = Query(default=20, ge=1, le=100),
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    return [para_saida(m) for m in MovimentacaoServico(db).listar(limite)]


@router.post("/{mov_id}/cancelar", response_model=RegistroSaida)
def cancelar(
    mov_id: uuid.UUID,
    dados: CancelamentoEntrada,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    mov, saldo = MovimentacaoServico(db).cancelar(usuario, mov_id, dados.motivo)
    return RegistroSaida(movimentacao=para_saida(mov), saldo_esperado=saldo)
