"""Hash de senhas (Argon2id) e emissão/validação de tokens JWT."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

# PasswordHasher usa Argon2id com salt aleatório por padrão.
_hasher = PasswordHasher()


def gerar_hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerificationError, InvalidHashError):
        return False


def criar_token(usuario_id: uuid.UUID, perfil: str) -> tuple[str, str]:
    jti = uuid.uuid4().hex
    expira = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expira_horas)
    payload = {"sub": str(usuario_id), "perfil": perfil, "jti": jti, "exp": expira}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), jti


def decodificar_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
