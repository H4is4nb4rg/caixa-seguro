"""Rotas do ciclo de caixa: resumo, abertura e fechamento."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas import AberturaEntrada, CaixaResumoPainel, CaixaSaida, FechamentoEntrada, PainelSaida, ResumoCaixa
from app.services import CaixaServico, PainelServico

router = APIRouter(prefix="/caixa", tags=["Caixa"])


@router.get("/atual", response_model=ResumoCaixa)
def caixa_atual(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    caixa, saldo, quantidade = CaixaServico(db).resumo()
    return ResumoCaixa(
        caixa=CaixaSaida.model_validate(caixa) if caixa else None,
        saldo_esperado=saldo,
        quantidade_movimentacoes=quantidade,
    )


@router.post("/abrir", response_model=CaixaSaida, status_code=201)
def abrir(dados: AberturaEntrada, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return CaixaServico(db).abrir(usuario, dados.valor_inicial)


@router.post("/fechar", response_model=CaixaSaida)
def fechar(dados: FechamentoEntrada, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return CaixaServico(db).fechar(usuario, dados.valor_contado, dados.justificativa)


@router.get("/painel", response_model=PainelSaida)
def painel(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    dados = PainelServico(db).montar(usuario)
    if dados["caixa_atual"] is not None:
        dados["caixa_atual"] = CaixaResumoPainel.model_validate(dados["caixa_atual"], from_attributes=True)
    dados["caixas_com_diferenca"] = [
        CaixaResumoPainel.model_validate(c, from_attributes=True) for c in dados["caixas_com_diferenca"]
    ]
    return dados
