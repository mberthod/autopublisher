from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:////data/home-mathieu/saas-rse/bloc-1-backend/data/saas_rse.db"
    log_level: str = "INFO"
    app_env: str = "development"

    # Ollama expose une API OpenAI-compatible sur :11434/v1
    deepseek_api_key: str = "ollama"
    deepseek_base_url: str = "http://localhost:11434/v1"
    deepseek_model: str = "deepseek-v4-flash:cloud"


settings = Settings()
