from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    user_service_url: str
    event_service_url: str
    invitation_service_url: str
    internal_api_key: str
    gateway_title: str
    gateway_version: str
    service_name: str
    cors_origins: str
    serve_frontend: bool
    frontend_dir: str | None = None
    http_timeout: float
    docs_url: str
    redoc_url: str
    openapi_url: str

    @field_validator("serve_frontend", mode="before")
    @classmethod
    def parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def resolved_frontend_dir(self) -> Path | None:
        if not self.serve_frontend:
            return None
        if self.frontend_dir:
            path = Path(self.frontend_dir)
            return path if path.is_dir() else None
        here = Path(__file__).resolve().parent
        for candidate in (
            here.parent / "frontend",
            here.parent.parent.parent.parent / "frontend",
        ):
            if candidate.is_dir():
                return candidate
        return None


settings = Settings()
