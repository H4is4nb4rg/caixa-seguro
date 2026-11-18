"""Configurações da aplicação, lidas de variáveis de ambiente (nunca do código)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./caixa_seguro.db"
    jwt_secret: str = "chave-de-desenvolvimento-troque-em-producao-0000"
    jwt_algorithm: str = "HS256"
    jwt_expira_horas: int = 8
    cors_origins: str = "http://localhost:4200"
    ambiente: str = "desenvolvimento"
    login_max_tentativas: int = 5
    login_bloqueio_minutos: int = 15

    @property
    def lista_cors(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origins.split(",") if origem.strip()]

    @property
    def producao(self) -> bool:
        return self.ambiente == "producao"


CHAVE_PADRAO_DESENVOLVIMENTO = "chave-de-desenvolvimento-troque-em-producao-0000"


def validar_configuracao(config: Settings) -> None:
    """Impede que a API rode em produção com a chave JWT de desenvolvimento."""
    if config.producao and (config.jwt_secret == CHAVE_PADRAO_DESENVOLVIMENTO or len(config.jwt_secret) < 32):
        raise RuntimeError("Defina JWT_SECRET com pelo menos 32 caracteres antes de iniciar em produção.")


settings = Settings()
validar_configuracao(settings)
