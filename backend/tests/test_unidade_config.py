"""Teste unitário da validação de configuração em produção."""
import pytest

from app.config import CHAVE_PADRAO_DESENVOLVIMENTO, Settings, validar_configuracao


def test_producao_recusa_chave_padrao():
    config = Settings(ambiente="producao", jwt_secret=CHAVE_PADRAO_DESENVOLVIMENTO)
    with pytest.raises(RuntimeError):
        validar_configuracao(config)


def test_producao_recusa_chave_curta():
    with pytest.raises(RuntimeError):
        validar_configuracao(Settings(ambiente="producao", jwt_secret="curta"))


def test_producao_aceita_chave_forte():
    validar_configuracao(Settings(ambiente="producao", jwt_secret="x" * 48))


def test_desenvolvimento_aceita_chave_padrao():
    validar_configuracao(Settings(ambiente="desenvolvimento", jwt_secret=CHAVE_PADRAO_DESENVOLVIMENTO))
