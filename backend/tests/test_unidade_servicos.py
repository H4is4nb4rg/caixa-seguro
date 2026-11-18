"""Testes unitários das regras de negócio (camada de serviços), sem passar pela API."""
from decimal import Decimal

import pytest

from app.models import Movimentacao
from app.security import gerar_hash_senha, verificar_senha
from app.services import (
    CaixaServico,
    ErroNegocio,
    MovimentacaoServico,
    calcular_saldo_esperado,
    efeito_no_dinheiro,
)

D = Decimal


def mov(tipo, valor, forma=None, cancelada=False):
    return Movimentacao(tipo=tipo, valor=D(valor), forma_pagamento=forma, cancelada=cancelada)


# ---------- cálculo do saldo esperado em dinheiro ----------

def test_venda_em_dinheiro_entra_na_gaveta():
    assert efeito_no_dinheiro(mov("venda", "50.00", "dinheiro")) == D("50.00")


def test_venda_em_pix_nao_altera_a_gaveta():
    assert efeito_no_dinheiro(mov("venda", "189.90", "pix")) == D("0.00")


def test_sangria_retira_dinheiro():
    assert efeito_no_dinheiro(mov("sangria", "100.00")) == D("-100.00")


def test_movimentacao_cancelada_nao_conta():
    assert efeito_no_dinheiro(mov("venda", "80.00", "dinheiro", cancelada=True)) == D("0.00")


def test_saldo_esperado_do_exemplo_do_prototipo():
    # Valor inicial 150,00 + entradas em dinheiro 562,40 - sangria 100,00 = 612,40
    movimentacoes = [
        mov("venda", "462.40", "dinheiro"),
        mov("venda", "100.00", "dinheiro"),
        mov("venda", "189.90", "pix"),
        mov("sangria", "100.00"),
    ]
    assert calcular_saldo_esperado(D("150.00"), movimentacoes) == D("612.40")


# ---------- senhas ----------

def test_senha_e_armazenada_como_hash_argon2id():
    senha_hash = gerar_hash_senha("SenhaFicticia#2026")
    assert senha_hash.startswith("$argon2id$")
    assert "SenhaFicticia#2026" not in senha_hash
    assert verificar_senha("SenhaFicticia#2026", senha_hash)
    assert not verificar_senha("senha-errada", senha_hash)


# ---------- regras do caixa ----------

def test_vendedora_nao_pode_abrir_caixa(db, usuarias):
    with pytest.raises(ErroNegocio) as erro:
        CaixaServico(db).abrir(usuarias["vendedora"], D("100.00"))
    assert erro.value.status_code == 403


def test_nao_permite_dois_caixas_abertos(db, usuarias):
    CaixaServico(db).abrir(usuarias["caixa"], D("100.00"))
    with pytest.raises(ErroNegocio) as erro:
        CaixaServico(db).abrir(usuarias["caixa"], D("50.00"))
    assert erro.value.mensagem == "Já existe um caixa aberto."


def test_nao_registra_movimentacao_sem_caixa_aberto(db, usuarias):
    with pytest.raises(ErroNegocio) as erro:
        MovimentacaoServico(db).registrar(usuarias["caixa"], "venda", D("10.00"), "pix", None)
    assert erro.value.status_code == 409


def test_responsavel_e_definido_pelo_servidor(db, usuarias):
    CaixaServico(db).abrir(usuarias["caixa"], D("100.00"))
    registro, _ = MovimentacaoServico(db).registrar(usuarias["vendedora"], "venda", D("10.00"), "pix", None)
    assert registro.usuario_id == usuarias["vendedora"].id
    assert registro.registrado_em is not None


def test_fechamento_com_diferenca_exige_justificativa(db, usuarias):
    servico = CaixaServico(db)
    servico.abrir(usuarias["caixa"], D("100.00"))
    MovimentacaoServico(db).registrar(usuarias["caixa"], "venda", D("50.00"), "dinheiro", None)
    with pytest.raises(ErroNegocio) as erro:
        servico.fechar(usuarias["caixa"], D("140.00"), None)
    assert erro.value.mensagem == "Explique a diferença para fechar o caixa."


def test_fechamento_calcula_divergencia(db, usuarias):
    servico = CaixaServico(db)
    servico.abrir(usuarias["caixa"], D("100.00"))
    MovimentacaoServico(db).registrar(usuarias["caixa"], "venda", D("50.00"), "dinheiro", None)
    caixa = servico.fechar(usuarias["caixa"], D("140.00"), "Troco dado a mais")
    assert caixa.status == "fechado"
    assert caixa.valor_esperado == D("150.00")
    assert caixa.divergencia == D("-10.00")


def test_cancelamento_preserva_registro_e_atualiza_saldo(db, usuarias):
    CaixaServico(db).abrir(usuarias["caixa"], D("100.00"))
    servico = MovimentacaoServico(db)
    registro, saldo = servico.registrar(usuarias["caixa"], "venda", D("30.00"), "dinheiro", None)
    assert saldo == D("130.00")
    cancelada, saldo = servico.cancelar(usuarias["caixa"], registro.id, "Valor digitado errado")
    assert cancelada.cancelada is True
    assert cancelada.cancelada_por_id == usuarias["caixa"].id
    assert saldo == D("100.00")
