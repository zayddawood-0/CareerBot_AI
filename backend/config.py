"""
Application-wide settings, loaded from environment variables / .env.
Import `settings` anywhere you need a config value instead of calling
os.environ directly — this keeps all config in one auditable place.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # AI providers
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./careerbot.db"

    # Agent schedule (24h format)
    agent_run_hour: int = 9
    agent_run_minute: int = 0

    # Server
    cors_origins: str = "http://localhost:5173"
    secret_key: str = "dev-secret-key"
    upload_dir: str = "./uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # lru_cache means the .env file is only parsed once per process
    return Settings()


settings = get_settings()
