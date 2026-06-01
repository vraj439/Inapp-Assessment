from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    user_service_url: str = "http://user-service:8001"
    event_service_url: str = "http://event-service:8002"
    invitation_service_url: str = "http://invitation-service:8003"
    internal_api_key: str = "dev-internal-key-change-in-production"
    gateway_title: str = "Event Scheduling API"


settings = Settings()
