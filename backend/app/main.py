"""Ponto de entrada da API do Caixa Seguro."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import auth, caixa, movimentacoes
from app.services import ErroNegocio

logger = logging.getLogger("caixa_seguro")


def criar_app() -> FastAPI:
    app = FastAPI(
        title="Caixa Seguro API",
        version="0.1.0",
        description="Controle e rastreabilidade do caixa da Maria Bunita Moda.",
        docs_url=None if settings.producao else "/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.lista_cors,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def cabecalhos_seguranca(request: Request, call_next):
        resposta = await call_next(request)
        resposta.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        return resposta

    @app.exception_handler(ErroNegocio)
    async def erro_negocio(_: Request, exc: ErroNegocio):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensagem})

    @app.exception_handler(Exception)
    async def erro_inesperado(_: Request, exc: Exception):
        # Detalhes técnicos ficam apenas no log interno, nunca na resposta.
        logger.exception("Erro inesperado: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Não foi possível concluir a operação."})

    @app.get("/saude", tags=["Infra"])
    def saude():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(caixa.router)
    app.include_router(movimentacoes.router)
    return app


Base.metadata.create_all(bind=engine)
app = criar_app()
