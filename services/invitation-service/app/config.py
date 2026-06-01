from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    event_service_url: str
    user_service_url: str
    internal_api_key: str
    service_name: str


settings = Settings()
