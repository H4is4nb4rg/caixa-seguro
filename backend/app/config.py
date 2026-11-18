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


settings = Settings()
