from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://users:users_secret@localhost:5432/users_db"
    internal_api_key: str = "dev-internal-key-change-in-production"
    service_name: str = "user-service"


settings = Settings()
