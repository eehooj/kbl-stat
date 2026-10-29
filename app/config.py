from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./kbl_predictor.db"
    kbl_request_delay_seconds: float = 1.5
    kbl_http_timeout_seconds: float = 20.0
    kbl_user_agent: str = "kbl-predictor/0.1 (non-commercial research)"
    kbl_browser_channel: str = "chrome"
    kbl_browser_user_data_dir: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
