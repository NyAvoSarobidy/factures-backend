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
    app_env: str = "development"
    app_port: int = 8000

    # Hermes
    hermes_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
