from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://invitations:invitations_secret@localhost:5432/invitations_db"
    )
    event_service_url: str = "http://localhost:8002"
    user_service_url: str = "http://localhost:8001"
    internal_api_key: str = "dev-internal-key-change-in-production"
    service_name: str = "invitation-service"


settings = Settings()
