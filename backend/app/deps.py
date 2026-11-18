"""Dependências da API: identificação da usuária autenticada em cada requisição."""
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.repositories import TokenRepositorio, UsuarioRepositorio
from app.security import decodificar_token

COOKIE_NOME = "caixa_seguro_token"


def _extrair_token(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NOME)
    if token:
        return token
    cabecalho = request.headers.get("Authorization", "")
    if cabecalho.lower().startswith("bearer "):
        return cabecalho[7:]
    return None


def payload_atual(request: Request, db: Session = Depends(get_db)) -> dict:
    token = _extrair_token(request)
    payload = decodificar_token(token) if token else None
    if payload is None or TokenRepositorio(db).revogado(payload.get("jti", "")):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre novamente.")
    return payload


def usuario_atual(payload: dict = Depends(payload_atual), db: Session = Depends(get_db)) -> Usuario:
    try:
        usuario = UsuarioRepositorio(db).por_id(uuid.UUID(payload["sub"]))
    except (KeyError, ValueError):
        usuario = None
    if usuario is None or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre novamente.")
    return usuario
