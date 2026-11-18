"""Esquemas Pydantic: validação obrigatória de todos os dados que entram e saem da API."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator
from typing import Annotated

Perfil = Literal["proprietaria", "caixa", "vendedora"]
TipoMovimentacao = Literal["venda", "desconto", "troca", "sangria", "pagamento"]
FormaPagamento = Literal["dinheiro", "pix", "debito", "credito"]
Dinheiro = Decimal


def _garantir_utc(valor: datetime | None) -> datetime | None:
    """Bancos como o SQLite devolvem datas sem fuso; todas são gravadas em UTC."""
    if valor is not None and valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


DataUTC = Annotated[datetime, AfterValidator(_garantir_utc)]


class LoginEntrada(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=128)


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    login: str
    perfil: Perfil
    ativo: bool


class LoginSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioSaida


class AberturaEntrada(BaseModel):
    valor_inicial: Dinheiro = Field(ge=0, max_digits=10, decimal_places=2)


class FechamentoEntrada(BaseModel):
    valor_contado: Dinheiro = Field(ge=0, max_digits=10, decimal_places=2)
    justificativa: str | None = Field(default=None, max_length=300)


class CaixaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    valor_inicial: Dinheiro
    aberto_em: DataUTC
    usuario_abertura_id: uuid.UUID
    fechado_em: DataUTC | None = None
    usuario_fechamento_id: uuid.UUID | None = None
    valor_esperado: Dinheiro | None = None
    valor_contado: Dinheiro | None = None
    divergencia: Dinheiro | None = None
    justificativa: str | None = None


class ResumoCaixa(BaseModel):
    caixa: CaixaSaida | None
    saldo_esperado: Dinheiro | None = None
    quantidade_movimentacoes: int = 0


class MovimentacaoEntrada(BaseModel):
    # O identificador pode ser gerado no aparelho (modo offline); responsável e horário NUNCA vêm daqui.
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    tipo: TipoMovimentacao
    valor: Dinheiro = Field(gt=0, max_digits=10, decimal_places=2)
    forma_pagamento: FormaPagamento | None = None
    observacao: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def venda_exige_forma_pagamento(self):
        if self.tipo == "venda" and self.forma_pagamento is None:
            raise ValueError("Informe a forma de pagamento da venda.")
        return self


class CancelamentoEntrada(BaseModel):
    motivo: str = Field(min_length=3, max_length=200)


class MovimentacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    caixa_id: uuid.UUID
    usuario_id: uuid.UUID
    responsavel: str
    tipo: TipoMovimentacao
    valor: Dinheiro
    forma_pagamento: FormaPagamento | None
    observacao: str | None
    registrado_em: DataUTC
    cancelada: bool
    motivo_cancelamento: str | None
    cancelada_por_id: uuid.UUID | None


class RegistroSaida(BaseModel):
    movimentacao: MovimentacaoSaida
    saldo_esperado: Dinheiro


class TotalPorChave(BaseModel):
    chave: str
    quantidade: int
    total: Dinheiro


class CaixaResumoPainel(BaseModel):
    id: uuid.UUID
    status: str
    aberto_em: DataUTC
    fechado_em: DataUTC | None = None
    divergencia: Dinheiro | None = None
    justificativa: str | None = None


class PainelSaida(BaseModel):
    caixa_atual: CaixaResumoPainel | None
    total_vendas: Dinheiro
    quantidade_vendas: int
    saldo_esperado_dinheiro: Dinheiro | None
    quantidade_canceladas: int
    por_forma_pagamento: list[TotalPorChave]
    por_responsavel: list[TotalPorChave]
    caixas_com_diferenca: list[CaixaResumoPainel]
