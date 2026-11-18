"""Testes de integração: percorrem a API completa (rotas, serviços, repositórios e banco)."""
import uuid

from conftest import SENHA_TESTE, entrar


# ---------- autenticação (RF01 / RNF01) ----------

def test_login_valido_retorna_perfil(client):
    resposta = client.post("/auth/login", json={"login": "carla", "senha": SENHA_TESTE})
    assert resposta.status_code == 200
    assert resposta.json()["usuario"]["perfil"] == "caixa"
    assert "senha_hash" not in resposta.text
    assert "httponly" in resposta.headers["set-cookie"].lower()


def test_login_invalido_tem_mensagem_generica(client):
    errada = client.post("/auth/login", json={"login": "carla", "senha": "errada"})
    inexistente = client.post("/auth/login", json={"login": "ninguem", "senha": "errada"})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json() == {"detail": "Login ou senha inválidos."}


def test_usuaria_inativa_nao_entra(client):
    resposta = client.post("/auth/login", json={"login": "dora", "senha": SENHA_TESTE})
    assert resposta.status_code == 401


def test_bloqueio_apos_cinco_tentativas(client):
    for _ in range(5):
        client.post("/auth/login", json={"login": "bia", "senha": "errada"})
    resposta = client.post("/auth/login", json={"login": "bia", "senha": SENHA_TESTE})
    assert resposta.status_code == 429


def test_rota_protegida_sem_token_retorna_401(client):
    assert client.get("/caixa/atual").status_code == 401


def test_logout_revoga_o_token(client):
    cab = entrar(client, "carla")
    assert client.post("/auth/logout", headers=cab).status_code == 204
    assert client.get("/auth/me", headers=cab).status_code == 401


# ---------- fluxo central (RF02, RF03, RF04, RF05) ----------

def test_fluxo_completo_do_caixa(client):
    cab = entrar(client, "carla")

    assert client.post("/caixa/abrir", json={"valor_inicial": "150.00"}, headers=cab).status_code == 201

    venda = client.post(
        "/movimentacoes", json={"tipo": "venda", "valor": "189.90", "forma_pagamento": "pix"}, headers=cab
    )
    assert venda.status_code == 201
    corpo = venda.json()
    assert corpo["movimentacao"]["responsavel"] == "Carla"
    assert corpo["saldo_esperado"] == "150.00"  # PIX não entra na gaveta

    client.post("/movimentacoes", json={"tipo": "venda", "valor": "562.40", "forma_pagamento": "dinheiro"}, headers=cab)
    client.post("/movimentacoes", json={"tipo": "sangria", "valor": "100.00"}, headers=cab)

    resumo = client.get("/caixa/atual", headers=cab).json()
    assert resumo["saldo_esperado"] == "612.40"
    assert resumo["quantidade_movimentacoes"] == 3

    sem_justificativa = client.post("/caixa/fechar", json={"valor_contado": "602.40"}, headers=cab)
    assert sem_justificativa.status_code == 422
    assert sem_justificativa.json()["detail"] == "Explique a diferença para fechar o caixa."

    fechado = client.post(
        "/caixa/fechar", json={"valor_contado": "602.40", "justificativa": "Troco dado a mais"}, headers=cab
    )
    assert fechado.status_code == 200
    assert fechado.json()["divergencia"] == "-10.00"

    depois = client.post("/movimentacoes", json={"tipo": "sangria", "valor": "10.00"}, headers=cab)
    assert depois.status_code == 409


def test_cancelamento_mantem_historico(client):
    cab = entrar(client, "carla")
    client.post("/caixa/abrir", json={"valor_inicial": "100.00"}, headers=cab)
    mov = client.post(
        "/movimentacoes", json={"tipo": "venda", "valor": "30.00", "forma_pagamento": "dinheiro"}, headers=cab
    ).json()["movimentacao"]

    cancelada = client.post(f"/movimentacoes/{mov['id']}/cancelar", json={"motivo": "Valor errado"}, headers=cab)
    assert cancelada.status_code == 200
    assert cancelada.json()["saldo_esperado"] == "100.00"

    historico = client.get("/movimentacoes", headers=cab).json()
    assert historico[0]["cancelada"] is True
    assert historico[0]["motivo_cancelamento"] == "Valor errado"


def test_nao_existe_rota_de_exclusao(client):
    cab = entrar(client, "carla")
    resposta = client.delete(f"/movimentacoes/{uuid.uuid4()}", headers=cab)
    assert resposta.status_code in (404, 405)


def test_sincronizacao_offline_nao_duplica(client):
    cab = entrar(client, "carla")
    client.post("/caixa/abrir", json={"valor_inicial": "0"}, headers=cab)
    corpo = {"id": str(uuid.uuid4()), "tipo": "venda", "valor": "20.00", "forma_pagamento": "dinheiro"}
    client.post("/movimentacoes", json=corpo, headers=cab)
    client.post("/movimentacoes", json=corpo, headers=cab)
    assert client.get("/caixa/atual", headers=cab).json()["quantidade_movimentacoes"] == 1


# ---------- autorização e validação (RNF02 / OWASP) ----------

def test_vendedora_nao_fecha_caixa(client):
    cab_caixa = entrar(client, "carla")
    client.post("/caixa/abrir", json={"valor_inicial": "100.00"}, headers=cab_caixa)
    cab_vendedora = entrar(client, "bia")
    resposta = client.post("/caixa/fechar", json={"valor_contado": "100.00"}, headers=cab_vendedora)
    assert resposta.status_code == 403


def test_responsavel_enviado_pela_interface_e_rejeitado(client):
    cab = entrar(client, "bia")
    entrar_caixa = entrar(client, "carla")
    client.post("/caixa/abrir", json={"valor_inicial": "0"}, headers=entrar_caixa)
    resposta = client.post(
        "/movimentacoes",
        json={"tipo": "venda", "valor": "10.00", "forma_pagamento": "pix", "usuario_id": str(uuid.uuid4())},
        headers=cab,
    )
    assert resposta.status_code == 422


def test_valor_negativo_ou_tipo_invalido_retorna_422(client):
    cab = entrar(client, "carla")
    client.post("/caixa/abrir", json={"valor_inicial": "0"}, headers=cab)
    negativo = client.post("/movimentacoes", json={"tipo": "venda", "valor": "-5", "forma_pagamento": "pix"}, headers=cab)
    invalido = client.post("/movimentacoes", json={"tipo": "roubo", "valor": "5"}, headers=cab)
    assert negativo.status_code == invalido.status_code == 422


def test_injecao_sql_no_login_nao_autentica(client):
    resposta = client.post("/auth/login", json={"login": "' OR '1'='1", "senha": "' OR '1'='1"})
    assert resposta.status_code == 401


def test_texto_com_script_e_gravado_como_texto(client):
    cab = entrar(client, "carla")
    client.post("/caixa/abrir", json={"valor_inicial": "0"}, headers=cab)
    script = "<script>alert(1)</script>"
    resposta = client.post(
        "/movimentacoes",
        json={"tipo": "venda", "valor": "10.00", "forma_pagamento": "pix", "observacao": script},
        headers=cab,
    )
    assert resposta.json()["movimentacao"]["observacao"] == script
    assert resposta.headers["content-type"].startswith("application/json")
    assert "default-src 'self'" in resposta.headers["content-security-policy"]


def test_erro_inesperado_nao_expoe_detalhes(client, monkeypatch):
    from app.services import CaixaServico

    def explode(*_):
        raise RuntimeError("SELECT * FROM usuario -- detalhe interno")

    monkeypatch.setattr(CaixaServico, "resumo", explode)
    cab = entrar(client, "carla")
    resposta = client.get("/caixa/atual", headers=cab)
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Não foi possível concluir a operação."}
