import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import criar_app
from app.models import Usuario
from app.security import gerar_hash_senha
from app.services import AutenticacaoServico

SENHA_TESTE = "SenhaFicticia#2026"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    sessao = Sessao()
    AutenticacaoServico.limpar_tentativas()
    yield sessao
    sessao.close()
    Base.metadata.drop_all(engine)


def _usuario(db, nome, login, perfil, ativo=True):
    u = Usuario(nome=nome, login=login, senha_hash=gerar_hash_senha(SENHA_TESTE), perfil=perfil, ativo=ativo)
    db.add(u)
    db.commit()
    return u


@pytest.fixture()
def usuarias(db):
    return {
        "proprietaria": _usuario(db, "Silvia", "silvia", "proprietaria"),
        "caixa": _usuario(db, "Carla", "carla", "caixa"),
        "vendedora": _usuario(db, "Bia", "bia", "vendedora"),
        "inativa": _usuario(db, "Dora", "dora", "vendedora", ativo=False),
    }


@pytest.fixture()
def client(db, usuarias):
    app = criar_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def entrar(client, login):
    resposta = client.post("/auth/login", json={"login": login, "senha": SENHA_TESTE})
    assert resposta.status_code == 200, resposta.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}
