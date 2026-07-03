from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:////data/home-mathieu/saas-rse/bloc-1-backend/data/saas_rse.db"
    log_level: str = "INFO"
    app_env: str = "development"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    queue_poll_interval_seconds: int = 5
    queue_max_retries: int = 3
    queue_backoff_base_seconds: int = 1
    queue_jitter_factor: float = 0.2
    queue_stuck_threshold_minutes: int = 5


settings = Settings()
