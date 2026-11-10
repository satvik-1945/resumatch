from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    web_origin: str = "http://localhost:3000"
    web_additional_origins: list[str] = ["http://127.0.0.1:3000"]
    cookie_secure: bool = False
    registration_enabled: bool = True
    llm_api_key: SecretStr | None = None
    llm_base_url: str = ""
    llm_model: str = ""

    @field_validator("llm_base_url")
    @classmethod
    def llm_url(cls, value):
        if not value:
            return value
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("LLM_BASE_URL must be an HTTPS endpoint without credentials or query")
        return value.rstrip("/")

    @field_validator("database_url")
    @classmethod
    def postgres(cls, value):
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg://; see .env.example")
        return value

    @field_validator("web_origin")
    @classmethod
    def origin(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
        ):
            raise ValueError("Use an origin such as http://localhost:3000 with no trailing slash")
        _ = parsed.port
        return value

    @field_validator("web_additional_origins")
    @classmethod
    def origins(cls, values):
        return [cls.origin(value) for value in values]


@lru_cache
def get_settings():
    return Settings()
