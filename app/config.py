from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_port: int = 8000
    app_secret_key: str = "change-me"

    # Banco de dados
    database_url: str = "postgresql+asyncpg://gcfinder:gcfinder@db:5432/gcfinder"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_access_secret: str = "change-me-access"
    jwt_refresh_secret: str = "change-me-refresh"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Google Maps
    google_maps_api_key: str = ""

    # Google Forms
    google_forms_submit_url: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
