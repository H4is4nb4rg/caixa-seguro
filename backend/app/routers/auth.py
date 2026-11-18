"""Rotas de autenticação: entrar, sair e consultar a usuária logada."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import COOKIE_NOME, payload_atual, usuario_atual
from app.models import Usuario
from app.schemas import LoginEntrada, LoginSaida, UsuarioSaida
from app.services import AutenticacaoServico

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=LoginSaida)
def login(dados: LoginEntrada, response: Response, db: Session = Depends(get_db)):
    token, usuario = AutenticacaoServico(db).entrar(dados.login, dados.senha)
    response.set_cookie(
        COOKIE_NOME,
        token,
        httponly=True,
        secure=settings.producao,
        samesite="strict",
        max_age=settings.jwt_expira_horas * 3600,
    )
    return LoginSaida(access_token=token, usuario=UsuarioSaida.model_validate(usuario))


@router.post("/logout", status_code=204)
def logout(response: Response, payload: dict = Depends(payload_atual), db: Session = Depends(get_db)):
    AutenticacaoServico(db).sair(payload["jti"])
    response.delete_cookie(COOKIE_NOME)


@router.get("/me", response_model=UsuarioSaida)
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario
