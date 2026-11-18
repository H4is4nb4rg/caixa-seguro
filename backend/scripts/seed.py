"""Cria as usuárias iniciais da loja (dados fictícios para desenvolvimento e validação).

Uso: python -m scripts.seed
As senhas temporárias são lidas da variável SENHA_INICIAL e devem ser trocadas no primeiro acesso.
"""
import os

from app.database import Base, SessionLocal, engine
from app.models import Usuario
from app.security import gerar_hash_senha

USUARIAS = [
    ("Proprietária", "proprietaria", "proprietaria"),
    ("Carla", "carla", "caixa"),
    ("Bia", "bia", "vendedora"),
]


def main() -> None:
    senha = os.environ.get("SENHA_INICIAL")
    if not senha or len(senha) < 8:
        raise SystemExit("Defina SENHA_INICIAL com pelo menos 8 caracteres.")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for nome, login, perfil in USUARIAS:
            if db.query(Usuario).filter_by(login=login).first() is None:
                db.add(Usuario(nome=nome, login=login, perfil=perfil, senha_hash=gerar_hash_senha(senha)))
        db.commit()
    print("Usuárias criadas: " + ", ".join(login for _, login, _ in USUARIAS))


if __name__ == "__main__":
    main()
