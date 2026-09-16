from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""

    # App
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    # Clé API interne — protège les endpoints confidentiels
    INTERNAL_API_KEY: str = ""

    # Hermes
    HERMES_API_KEY: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
